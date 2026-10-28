# 1. Firmware container (`usb_*.bin` / `MstarUpgrade.bin`)

**Русская версия: [docs/ru/01-firmware-container.md](ru/01-firmware-container.md)**

Sample obtained from Hisense support on request, delivered by the German
distributor as a signed Salesforce download link. Nothing here requires that
file: verify your own copy with the hash below.

| | |
|---|---|
| File name | `MstarUpgrade.bin` (also distributed as `usb_MTK_9603_EU_4K_2G_3_YT25.bin`) |
| Size | 1 005 336 192 bytes (`0x3bec3680`) |
| SHA-256 | `f366894eadf26f79fc85d0bb06cd2c35bc171a539ebdd3f440f0ef2ec452c5ac` |

## Layout

```
0x000000  256 bytes      RSA-2048 signature block (opaque)
0x000100  "V_0.0.0"      packer version, null-padded to 0x300
0x000302  plaintext      "# REE_OFFSET_START = 0x1000 #\n# REE_OFFSET_LEN = 0x3bec0000 #\n"
0x001000  payload        AES body, 0x3bec0000 bytes
0x3bec1000 tail          signature + manifest, 9856 bytes
```

Manifest, printable strings in the tail:

```
0x3bec3400  MTK_9603_EU_4K_2G_3_YT25
0x3bec3420  V0000.09.60V.Q0612
0x3bec3480  MT9603DB
0x3bec34a0  Hisense
```

The 9856-byte tail also contains 492 `0xFF` bytes, 166 zero bytes and 46 short
random printable runs — consistent with a signature plus fixed-field manifest,
not with compressed data.

## Payload analysis

| Test | Result |
|---|---|
| Shannon entropy, 4 MiB windows at 0x1000 / 0x100000 / mid / end | 7.9999 – 8.0000 |
| Repeated 16-byte blocks in a 64 MiB sample | 0 (4 194 303 unique) |
| Repeated 512-byte blocks, 64 MiB | 0 |
| Zero bytes in payload | 0.4 % |
| gzip / bzip2 / xz / zip / tar / squashfs / UBIFS / ELF / `ANDROID!` / `CrAU` signatures | none meaningful |
| `binwalk` 2.4.3 (first 128 MiB) | only false "JBOOT STAG" hits |

Full-entropy payload with **no block reuse** means CBC/CTR/XTS, not ECB — so a
dictionary attack over repeated plaintext blocks is impossible.

## Why the usual Hisense/MTK tooling fails

**`epk2extract`** (`openlgtv/epk2extract`) detects MTK packages by vendor magic
at **offset 0**:

```c
#define HISENSE_PKG_MAGIC "hise"
#define MTK_FIRMWARE_MAGIC "#DH@FiRm"
#define MTK_PAK_MAGIC      "iMtK8"
```

Scan of all 1 005 336 192 bytes: `hise` 0 hits, `#DH@FiRm` 0, `iMtK8` 0, plus
its `is_firm_image()` path expects an LZHS header after the firmware headers.
The container is not that format. Its bundled keys (`keys/MTK.key`) are the
public "Mediatek generic" AES-128 keys — `09291094…`, `53686172…` (Sharp),
`5450565F…` (TPV). Applied to the payload in ECB, CBC and CTR they produce
printable garbage with no recognisable magic. Its README states the actual
requirement plainly: for encrypted revisions, *"dump them from a running TV"*.

**REA** (`morlua/rea` / `rea-agents` 6.4.0) has `inspect-firmware-regions` and
`extract-firmware`, but both dispatch to binwalk and refuse to run without an
absolute `REA_BINWALK_COMMAND`. Even with binwalk wired up, extraction is
signature-driven, and there are no signatures to drive it.

**Fixed-key brute force** (DES-ECB both keys, AES-128-ECB with
`0123456789ABCDEF` and zeros, AES-256-ECB) produces no output either.

## Consequence

The body cannot be decrypted offline. The key lives on the device — in the boot
partition or in eFuse — so any further work needs device-side access (UART,
bootloader shell, or a key dump from a running system). The file itself remains
useful as a recovery image for the exact model/version, and as a reference to
compare against once a key is available.
