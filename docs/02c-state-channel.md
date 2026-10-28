# 2c. The one confirmed write channel: `TvInfo_setParam`

**Русская версия: [docs/ru/02c-state-channel.md](ru/02c-state-channel.md)**

Everything that touches files is gated. One thing is not: the state channel.
A page rendered by the TV can write device settings through a native function
with no application identity, no `appconfig` check and no session at all.

## How it is reached

`TvInfo_setParam(key, value)` is a global, next to `TvInfo_getParam`. The vendor
SDK itself uses it for the settings menu:

```js
vowOS.tvinfo.setBrightness = function (data) { return TvInfo_setParam('brightness', data) }
vowOS.tvinfo.setContrast   = function (data) { return TvInfo_setParam('contrast', data) }
```

Nothing stops a page from calling the function directly with any key.

## Which keys are live

Measured by reading a key and writing **the same value back** — a no-op for the
device, but enough to see whether the setter accepts the key:

| key | value on the test device | write |
|---|---|---|
| `brightness` | 50 | accepted |
| `contrast` | 80 | accepted |
| `kidsMode` | 0 | accepted |
| `storeMode` | 0 | accepted |
| `isHotelMode` | 0 | accepted |
| `magnificationEnable` | 0 | accepted |
| `ttsEnable` | 0 | accepted |
| `panelType` | 0 | accepted |
| `region` | `EU_A` | accepted |
| `featureCode` | redacted | accepted |
| `artMode`, `hotelMode`, `dabTools`, `volume`, `mute`, `country`, `source`, `menuScheme`, `menuTransparency` | `null` | no such key |

Ten live setters, nine names that do not exist. The accepted list is state, not
files — but it includes `isHotelMode`, `storeMode` and `region`, which are the
settings that normally require a service menu.

## Why it matters

This is the only write path on this firmware confirmed to work from an arbitrary
web page. It runs beside the `appconfig` gate rather than through it: the gate
covers `hiutils` (`fileWrite`, `deviceCode`, `uninstallApp`), while `TvInfo_*`
is a separate native surface that the permission check does not wrap.

Practical consequences:

- A page can flip shop/store mode and hotel mode without any identity. That is
  a configuration risk for a device that is left on a network with a browser.
- Combined with the WebSocket registration finding in
  [document four](04-identity-gate.md), it shows the permission model is
  per-service, not per-device: `hiutils` is locked, `tvinfo` is not.
- It still does not touch the filesystem. Reading `/etc/*` and writing files stay
  behind the same wall.

## Deliberately not exercised

`isHotelMode` and `region` were never changed. Writing the same value back is
harmless; writing a different one is not obviously reversible through the UI —
hotel mode in particular is known to trap users when the exit item is missing
from the settings menu on non-HL models, and `region` affects what the platform
thinks it may show. The mechanism is documented here so it can be used
deliberately if ever needed, with the knowledge that the same call reverts it.
