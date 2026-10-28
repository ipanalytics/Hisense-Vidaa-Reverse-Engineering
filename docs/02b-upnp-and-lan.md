# 2b. What the TV exposes to the LAN

Everything in [document two](02-local-services.md) is reachable only from inside
the TV. This one is the opposite view: what answers from another machine on the
same network.

## Ports

Paced single-port checks (see the note on method at the end):

```
open      36669   MQTT broker
open      18400   UPnP / DLNA MediaRenderer
closed    9226    chrome inspect — connection refused
filtered  9223    CDP — no response at all
closed    9222 9227 8080 8443 9443 8009 9009 9888
```

`9226` and `9223` are the two debug interfaces that older write-ups used to get
JavaScript running in more privileged contexts. On this build `9226` refuses
immediately and `9223` swallows packets, so neither exists as an entry point.
That closes the "cheap bypass of the identity gate through DevTools" idea for
this firmware.

`9888`, the service port used by the web layer, is **not** reachable from the
LAN — it listens on loopback only.

## 18400 — plain UPnP, no authentication

The port is a standard DLNA MediaRenderer, announced over SSDP and described at
`/MediaServer/rendererdevicedesc.xml`. The descriptor carries a `#CAP#` block
with platform parameters, which is where the interesting numbers are:

```
transport_protocol=3290   platform=1   voice=2   brand=his   vidaa_support=1   region=0
```

`transport_protocol=3290` is the marker for the modern VIDAA authentication
profile — the same value third-party integrations use to decide which MQTT
handshake to attempt.

Three services, all standard:

| Service | SCPD | Control |
|---|---|---|
| ConnectionManager:1 | `/MediaServer/cm.xml` | `/upnp/control/minguscmr` |
| AVTransport:1 | `/MediaServer/avt.xml` | `/upnp/control/mingusavtr` |
| RenderingControl:1 | `/MediaServer/rc.xml` | `/upnp/control/mingusrcr` |

Actions are exactly the ones the DLNA spec defines — `GetProtocolInfo`,
`GetCurrentConnectionIDs`, `GetCurrentConnectionInfo`; `SetAVTransportURI`,
`Play`, `Pause`, `Stop`, `Seek`, `GetPositionInfo` and friends; `GetVolume`,
`SetVolume`, `GetMute`, `SetMute`, `ListPresets`, `SelectPreset`. No vendor
actions, no custom arguments, nothing undocumented.

SOAP calls work without any authentication:

```
POST /upnp/control/minguscmr
SOAPAction: "urn:schemas-upnp-org:service:ConnectionManager:1#GetProtocolInfo"
→ 200, Source empty, Sink = the usual MIME list
```

Two observations worth keeping:

- `SetVolume` / `SetMute` and `SetAVTransportURI` are writes with no auth. That
  is normal for DLNA renderers and is not a path to code execution, but it does
  mean anything on the LAN can change the volume and push a media URL.
- The sink list contains `application/vnd.android.package-archive`. A renderer
  has no reason to advertise APK support; it is most likely a generic MIME table
  copied from the platform, not a hint that the renderer will install packages.
  Recorded as an oddity, not as a finding.

`/upnp/description.xml` does **not** exist here — it answers 404. The single
descriptor is the MediaServer one above.

## Why the port list needed a note

A parallel scan of all 65535 ports (400 workers, 0.7 s timeout) came back with
**nothing open**, which is wrong: the same script, run as single paced connects,
shows `36669` and `18400` open in under a millisecond. The TV drops SYNs under
scan load, so a burst scan produces false negatives and must not be published as
a result. Only per-port checks with a pause between them are trustworthy on this
device — worth remembering before reporting "the TV has no open ports" from a
fast scan.
