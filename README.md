# Hisense VIDAA (MT9603) — Reverse Engineering Notes

**Русская версия: [README.ru.md](README.ru.md)** · Russian readers start here.

These are field notes on how a Hisense TV running VIDAA on a Mediatek MT9603 is
put together — not through its menus, but through its own files, services and
protocols. Everything was collected on a TV I own, without reflashing it and
without changing its state. The point was to understand what is inside and how
it talks to the world, not to break a protection at any cost.

## Documentation

- [01. Firmware container](docs/01-firmware-container.md)
- [02. Local services on the TV](docs/02-local-services.md)
- [02b. What the TV exposes to the LAN](docs/02b-upnp-and-lan.md)
- [03. The `phoenix://` bridge protocol](docs/03-phoenix-protocol.md)
- [04. The identity / appconfig gate](docs/04-identity-gate.md)
- [05. Bridge surface: 96 host functions](docs/05-bridge-surface.md)
- [06. Negative results](docs/06-negative-results.md)
- [07. Tooling](docs/07-tooling.md)
- [08. Function map by firmware](docs/08-function-map.md)

Russian translations of every document live in [`docs/ru/`](docs/ru/).

## How this started

There is no direct firmware download for a specific Hisense model. The vendor
site offers a service request form; third-party archives such as FileWale and
HalabTech want money and an account; public mirrors carry other model lines.
The working route turned out to be unglamorous: an email to Hisense support with
the serial number, and a few days later a download link to `MstarUpgrade.bin`,
just under a gigabyte.

The first thing that file gave was not its contents but clarity: the image is
signed and encrypted, the key is not inside, and anything about the filesystem
would have to come off the TV itself. The second thing was insurance: if
experiments went wrong, there was a way back to exactly the version that was on
the device.

## Test device

| | |
|---|---|
| Panel model string | `65Q60SEVS_01` |
| SoC | `MTK9603` (Mediatek, ARMv7) |
| Software version | `V0000.09.60V.Q0612` |
| Build | `a20260727` |
| Region | `EU_A` |
| VIDAA SDK | `1.5.0` |
| Browser engine | Chromium 111, UA tokens `SurfMaster`, `PageReader`, `ViewPort` |

Serial number, device ID, capability and feature codes, MAC addresses and any
LAN addressing are removed from this repository. None of them say anything about
the platform; all of them point at one physical set.

## What the investigation found

The firmware is a signed container. The first 256 bytes are an RSA signature
block, then a packer version and two directives in clear text saying where the
payload starts and how long it is. The payload itself is ciphertext with entropy
close to eight bits per byte and not a single archive or filesystem signature.
The tail carries the manifest in plain text: platform, version, SoC, vendor. The
format is readable; the contents are not.

The usual MTK package tools do not apply. `epk2extract` looks for the magic
`hise` at offset zero, and there is a signature block there instead; its bundled
"generic" keys produce garbage in every mode. REA dispatches firmware work to
binwalk and would still be cutting on signatures that are not present. The
numbers behind all of this are in [document one](docs/01-firmware-container.md).

The second layer is the interesting one: the web side. Any page opened in the
TV's browser runs in an environment where the vendor exposes a bridge of 96
functions — firmware version, model, panel, region, TTS, subtitles, volume,
property observers. All of them are getters over a single native
`TvInfo_getParam`. The famous `Hisense_FileRead`, `File` and
`Hisense_installApp`, on which the 2017 write-ups rested, simply are not there
in this build, which closes the old recipes immediately.

What the old write-ups did not have is a local HTTP API at
`https://localhost:9888/service/<name>` that answers pages from a foreign
origin. There are exactly three services: `pkgmgr`, `hiutils` and `tvinfo`.
`tvinfo` returns device state, `pkgmgr` returns the installed package list with
paths like `APPS:pkgs/…`, and `hiutils` holds what the whole exercise is about:
`fileRead` and `fileWrite`.

That is where it stops. `fileRead` is allowed and does reach the filesystem, but
it builds its path from an application root, and for a page that is not an
installed application that root is `undefined`. `fileWrite`, `deviceCode` and
`uninstallApp` are refused with `client request permission check error, please
check appconfig`. The identity cannot be forged from JavaScript: the service
takes it from a native `vowOSContext`, and the native `init()` returns `-1` for
an ordinary page. The attempts and their results are tabulated in
[document four](docs/04-identity-gate.md), so nobody has to walk that path again.

## Where it ends

The web layer gave everything it had: the bridge map, three services, their API
whitelist, the message format of the `phoenix://` protocol, and the exact place
where permissions are checked. It did not give file access or a write path.

What remains needs a screwdriver: UART, a bootloader shell, a dump of the
partition holding the key. There is no UART document in this repository yet,
because there is no UART data yet — the repository does not carry empty
promises. When there is something, it will land here with the results.

## What is in this repository

```
docs/      analysis, one topic per file; docs/ru holds Russian translations
samples/   sanitized probe outputs (JSON) from the device
tools/     the HTML probe pages used to produce them (read-only)
```

The probe pages talk only to the machine that served them and call reads only:
`fileRead`, `getOSVersion`, `getVersionStatus`, `deviceCode`,
`getInstalledPkgs`, `tvinfo.initialData`. There is no write, no install and no
uninstall anywhere in them — the sources show it plainly.

The firmware image is not in the repository: it is a gigabyte, GitHub will not
take it, and it is somebody else's binary. What is here instead is the size, the
SHA-256 and the header layout, so that a copy obtained from vendor support can
be verified against these numbers.

## License

Code and probe pages: MIT. Text and documentation: CC BY 4.0.
