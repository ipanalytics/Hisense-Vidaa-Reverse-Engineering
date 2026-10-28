# 5. Bridge surface — 96 host functions

`window` on any page rendered by the TV browser is populated with the vendor
bridge. The inventory is collected by walking `window` for names matching
`Hisense_*`, `HiUtils*`, `Hi[A-Z]*`, `File`, `Vidaa*`, `WebAp*` and printing
`Function.prototype.toString()` of each — they are plain JavaScript, so the
sources are readable.

## What exists

96 functions. Grouped:

- **`Hisense_Get*` (≈80)** — every one is a getter over a native
  `TvInfo_getParam('<key>')`: model name, brand, region, country, panel
  resolution, firmware version, chipset, serial type, device ID, feature and
  capability codes, network state, IP address, volume/mute, TTS parameters,
  subtitle and closed-caption state, hotel-mode flag, and so on.
- **`Hisense_Set*`** — `SetVolume`, `SetRemoteKeyboard`, `setStartBandwidth`,
  `enableVKB` / `disableVKB`.
- **`Hisense_RegisterObserver` / `UnregisterObserver`** — key/callback pairs for
  property changes (`Hisense_RegisterVolumeObserver` wraps it for
  `soundVolume`).
- **`Hisense_LoginWithVIDAA(apptype, cb)`** — sends
  `{"type":"APPMessage","MsgType":"account","action":"loginWithVidaa",…}`
  through `omi_platform.sendPlatformMessage`.
- **`HiUtils_createRequest(type, msg)`** — the generic escape hatch to the
  native service (see `02-local-services.md`).

## What is missing

Compared with the 2017 VIDAA filesystem that circulates publicly, three
entry points are gone:

```
typeof Hisense_FileRead    → undefined
typeof File                → function   (the DOM File constructor, not a bridge object)
typeof Hisense_installApp  → undefined
```

That removal is the reason the older published technique — install an HTML5
app under `hisense://debug`, then read files through the bridge — no longer
applies to this revision.

`window.File` being `function` is a trap: it is `File` from the DOM, and
`File.read()` does not exist. A probe that tests `typeof File === 'function'` and
concludes "file API present" is wrong; the correct check is
`typeof File.read === 'function'`.

## Platform binding

`omi_platform` exposes exactly two methods:

```
omi_platform.addPlatformEventListener
omi_platform.sendPlatformMessage
```

`vowOS` exposes three:

```
vowOS.service   — the phoenix bridge (see 03-phoenix-protocol.md)
vowOS.tvinfo    — getters and setters over TvInfo_getParam/SetParam
vowOS.store     — getInstalledPkgs, installApp, sendPkgmgrRequest
```

`vowOS.tvinfo` includes setters (`setKidsMode`, `setArtMode`, `setBrightness`,
`setContrast`, `setDabTools`). They were not exercised: this investigation is
read-only. `vowOS.store.installApp` is dead on this revision — it forwards to
`Hisense_installApp`, which is undefined.
