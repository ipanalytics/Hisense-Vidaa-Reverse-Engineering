# Hisense VIDAA (MT9603) — Reverse Engineering Notes

Field notes from a **read-only** investigation of a Hisense TV running VIDAA on a
Mediatek **MT9603** SoC: how the USB firmware container is built, which local
services the TV exposes to the web layer, how the `phoenix://` bridge protocol
works, and where the permission gate sits.

Everything here was obtained from a device owned by the author, without
modifying it. No firmware images are redistributed. No exploit code is included:
the goal is documentation of interfaces (interoperability research), not a
jailbreak.

- Firmware container — [`docs/01-firmware-container.md`](docs/01-firmware-container.md)
- Local services on the TV — [`docs/02-local-services.md`](docs/02-local-services.md)
- `phoenix://` bridge protocol — [`docs/03-phoenix-protocol.md`](docs/03-phoenix-protocol.md)
- The identity / appconfig gate — [`docs/04-identity-gate.md`](docs/04-identity-gate.md)
- Bridge surface (96 host functions) — [`docs/05-bridge-surface.md`](docs/05-bridge-surface.md)
- Negative results (what does not work) — [`docs/06-negative-results.md`](docs/06-negative-results.md)
- Tooling — [`docs/07-tooling.md`](docs/07-tooling.md)

Russian version: [`README.ru.md`](README.ru.md).

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

Serial number, device ID, capability/feature codes, MAC addresses and any LAN
addressing are removed from this repository.

## Short version

1. **The USB firmware is RSA-signed and AES-encrypted.** Header: 256-byte RSA
   block at `0x000`, packer version `V_0.0.0` at `0x100`, plaintext directives
   at `0x302`:
   `# REE_OFFSET_START = 0x1000 #` and `# REE_OFFSET_LEN = 0x3bec0000 #`.
   The payload has entropy 7.9999–8.0000 across the whole range, zero repeated
   16-byte blocks in a 64 MiB sample, and no archive/filesystem signatures.
   The key is not in the file. The tail carries the manifest in plaintext:
   platform, version, SoC and vendor name.
2. **Well-known MTK package tools do not apply.** `epk2extract` detects Hisense
   packages by the magic `hise` at offset 0; this container has an RSA block
   there. Its public "Mediatek generic" AES keys (Hisense/Sharp/TPV) produce
   garbage in ECB, CBC and CTR on this payload.
3. **No `Hisense_FileRead`, no `File`, no `Hisense_installApp`.** The bridge
   exposes 96 functions and all of them are getters over `TvInfo_getParam`.
4. **Three local services are reachable from any document** rendered on the TV:
   `https://localhost:9888/service/{pkgmgr,hiutils,tvinfo}`. Their CORS policy
   allows reading responses from a foreign origin.
5. **`hiutils` has a small whitelist**: `fileRead`, `fileWrite`, `deviceCode`,
   `uninstallApp`, `getVersionStatus`, `getOSVersion`. Everything privileged
   answers `503 client request permission check error, please check appconfig`.
   `fileRead` is *allowed* but builds its path from an app-scoped root that is
   `undefined` for a page that is not an installed application.
6. **Identity cannot be forged from JavaScript.** `phoenix`/`service` take the
   caller identity from a native `vowOSContext`; `getIdentifier()` consults
   `vowOSContext.getAppIdentifier()`, whose native `init()` returns `-1` for a
   non-app page. Overriding `navigator.appIdentifier` and `vowOSContext` changes
   what the SDK sends, but not what the service checks.

Net result: the browser layer yields a full inventory of the bridge and the
service status, but no filesystem access and no write path. Going further
requires code execution outside the web layer (bootloader/UART territory).

## What is in this repository

```
docs/      analysis, one topic per file
samples/   sanitized probe outputs (JSON) from the device
tools/     the HTML probe pages used to produce them (read-only)
```

The probe pages talk only to the machine that serves them (`location.origin`),
so they can be dropped on any local web server. They call reads only: no
`fileWrite`, no `installApp`, no uninstall.

## Legal

- Decompilation for the purpose of interoperability is permitted in Germany
  under **§ 69e UrhG** (and Art. 6 of Directive 2009/24/EC) for a lawful user,
  when the information is not otherwise available, and only for the parts
  needed for interoperability. German text: <https://dejure.org/gesetze/UrhG/69e.html>
- The same provision restricts passing obtained information to third parties
  except where interoperability requires it. Therefore this repository contains
  **observations about interfaces** — formats, API names, message schemas, error
  codes, behaviour — and **no extracted code or binary blobs** of the vendor
  firmware.
- No firmware image is redistributed. The container is described by size,
  SHA-256 and header layout so that anyone can verify their own copy obtained
  from the vendor's support channel.
- No DRM circumvention, no bypass of paywalls or of the vendor's update
  signature, no instructions for breaking ABE or similar protections.

## License

Code and probe pages: MIT. Text and documentation: CC BY 4.0.
