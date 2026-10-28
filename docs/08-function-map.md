# 8. Function map by firmware

The bridge surface is not the same across VIDAA generations, and that difference
is the most useful single artefact here: it shows what a newer build takes away
and what it adds.

## Method

Two inventories, compared by name:

1. **This device** — 96 names collected by walking `window` on a page rendered by
   the TV itself, with `Function.prototype.toString()` for each. Nothing guessed;
   the list is what the firmware actually exposes.
2. **Reference library** — 113 distinct `Hisense_*` names as used by the public
   `vidaa-edge` project, which targets older VIDAA builds.

Comparison is case-insensitive, because the naming drifted on both sides
(`GetTvLogo` vs `GetTVLogo`, `GetWoWEnable` vs `GetWOWEnable`,
`GetMenuTransparency` vs `GetMenuTransparecy`, and so on). That gives 41 names
present in the reference library and absent here, and 23 present here and absent
there.

## 41 names gone in this build

These are the ones that matter, grouped by what they used to allow:

**Files and apps**

```
Hisense_FileRead          Hisense_FileWrite
Hisense_installApp        Hisense_installApp_V2
Hisense_uninstallApp      Hisense_getInstalledApps
```

**Service codes and crypto**

```
Hisense_CheckCodeValid    Hisense_CheckAccessCode
Hisense_Encrypt           Hisense_Decrypt          Hisense_RSADecrypt
Hisense_HiSdkSignCreate   Hisense_HiSdkSignCreateSoundbar
Hisense_HiSdkJsonVerifyHeap
```

**Debug surface**

```
Hisense_getDebugPort      Hisense_setDebugPort
Hisense_EnableDebugLog    Hisense_GetDebugLevelForHisenseUI
Hisense_PrintLogMessage   Hisense_WriteTvRunLog
Hisense_GetTestApiList
```

**Network**

```
Hisense_GetDNS            Hisense_SetDNS
Hisense_GetMacAddress     Hisense_GetUpdatesVerInfo
Hisense_ResetDevice
```

**Identity, rating and picture**

```
Hisense_GetCustomerID     Hisense_SetCustomerID
Hisense_GetRoleID         Hisense_SetRoleID
Hisense_GetMovieRating    Hisense_GetTvRating
Hisense_GetTvChildrenRating  Hisense_GetCanEngRating  Hisense_GetCanFreRating
Hisense_GetRatingEnable   Hisense_GetParentControls  Hisense_GetParentalControlEnabled
Hisense_GetPictureModeList   Hisense_SetPictureMode
```

## 23 names present only here

```
Hisense_GetArcMode            Hisense_GetAudioFormat       Hisense_GetAudioMode
Hisense_GetCCAtvChannel       Hisense_GetCCAtvSupport      Hisense_GetCCDtvService
Hisense_GetDatePattern        Hisense_GetDtvStandard       Hisense_GetFaderMode
Hisense_GetMagnification      Hisense_GetMagnificationEnable
Hisense_GetMenuTransparecy    Hisense_GetPrimarySubtitle   Hisense_GetSecondarySubtitle
Hisense_GetSubtitleMode       Hisense_GetSubtitleStorage   Hisense_GetSubtitleStyle
Hisense_GetSupportTTS         Hisense_GetTTSFocusAudio     Hisense_GetTTSSupportLanguage
Hisense_GetTunerSupport       Hisense_RegisterVolumeObserver   Hisense_SetVolume
```

The additions are all accessibility, subtitle, tuner and audio-detail getters —
the platform grew sideways, not deeper.

## What the map says

The interesting part is not the count but the shape of the cut. Everything that
touched files, service codes, cryptography, debugging and installation is gone;
everything the UI itself needs to draw a settings menu is still there.

That is consistent with what the services showed independently: the privileged
surface did not disappear, it moved behind the `appconfig` permission check in
`hiutils`, where a page can reach it by name but not by right. `fileWrite` and
`uninstallApp` are whitelisted APIs that answer `503`, not removed ones. So the
firmware did not delete the capability — it stopped handing it to unprivileged
callers.

Anyone comparing an older dump against `vidaa-edge` should expect a name-level
diff like this one; the JS layer is where the vendor makes changes between
builds, and it is cheap to measure.
