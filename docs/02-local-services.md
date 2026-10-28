# 2. Local services on the TV

Any HTML document rendered on the TV can reach the local service API:

```
https://localhost:9888/service/<name>
```

Port 9888 is **loopback only** — it is not reachable from the LAN, even though
the TV answers on other ports (for example 36669, its MQTT endpoint).

## Service inventory

Probing 54 plausible names, exactly three answer with `200`:

| Service | Behaviour |
|---|---|
| `pkgmgr` | package manager |
| `hiutils` | privileged utility API (file access, device codes) |
| `tvinfo` | TV state (read) |

Everything else — `file`, `files`, `tvapi`, `appconfig`, `system`, `upgrade`,
`ota`, `debug`, `shell`, `exec`, `log`, `network`, `settings`, `storage`,
`cert`, `factory`, `hotel`, `usb`, `screenshot`, … — returns:

```json
{"ret":false,"msg":"Wrong request:/service/<name>?api=...","code":500,"sdkVersion":"1.5.0"}
```

`GET https://localhost:9888/` answers `service register failed` with `503`,
i.e. the root is a registration endpoint, not a directory listing.

## CORS

Responses carry a permissive origin policy: a page served from a completely
different host could read the JSON bodies — that is how the inventory below was
collected. POSTing to the service from ordinary `XMLHttpRequest` fails on
preflight, which is why the vendor SDK uses *synchronous* XHR and sends its
messages through the WebSocket channel instead (see `03-phoenix-protocol.md`).

## `hiutils` — the interesting one

The service validates `api` against a whitelist and answers
`{"ret":false,"msg":"Not supported api","code":500}` for anything else.
Out of ~70 candidate names only these exist:

| api | Result on a non-installed page |
|---|---|
| `getOSVersion` | `{"ret":true,"msg":"U09.60"}` |
| `getVersionStatus` | `{"ret":true,"msg":"release"}` |
| `fileRead` | accepted (`code 0`) but path resolution fails |
| `fileWrite` | `503 client request permission check error, please check appconfig` |
| `deviceCode` | `503 …` same error |
| `uninstallApp` | `503 …` same error |

Two facts matter here:

1. The permission gate (`appconfig`) is a **separate, later check** than the
   whitelist. `fileWrite` exists, is whitelisted, and is refused at the
   permission layer — not at the API-name layer.
2. `fileRead` passes the permission layer and fails only on path construction,
   which means read access was not considered sensitive enough to gate.

### `fileRead` argument shape

```js
HiUtils_createRequest('fileRead', { path: '/etc/passwd' })
→ {"ret":false,"msg":{"errno":-2,"code":"ENOENT","syscall":"open",
                     "path":"undefined/etc/passwd"},"code":0}
```

The service concatenates **a caller-derived root** with `args.path`; for a page
that is not an installed application the root evaluates to `undefined`. Forty-five
candidate key names (`dir`, `root`, `base`, `baseDir`, `folder`, `prefix`, `mnt`,
`mount`, `dev`, `part`, `cwd`, `home`, `url`, `src`, …) were injected with a
marker value and none of them replaced the prefix — so the root is not taken
from the call arguments at all.

Path traversal is rejected by explicit validation before any syscall:

```
../../../../etc/version        → "invalid path:../../../../etc/version"
/../../etc/version             → "invalid path:/../../etc/version"
APPS:pkgs/../../etc/version    → "invalid path:APPS:pkgs/../../etc/version"
..%2f..%2f..%2fetc/version     → ENOENT on "undefined..%2f..%2f..%2fetc/version" (not decoded)
```

## `pkgmgr`

Only `getInstalledPkgs` works. The reply is a real package list, and it exposes
the virtual filesystem prefixes used by the platform:

```json
{"ret":true,"msg":[
  {"name":"tv.vidaa.app.browser","version":"9.6.0-r20260612v",
   "status":"install user installed","type":"ns",
   "path":"APPS:pkgs/tv.vidaa.app.browser/CHA/"},
  {"name":"tv.vidaa.res.iot","version":"1.0.1-r20260612v","type":"res",
   "path":"APPS:pkgs/tv.vidaa.res.iot/…"}
]}
```

`getAppInfo`, `getAppConfig`, `getPermissions`, `getAppList`, `getPkgInfo`,
`getStartupApps`, `getRunningApps`, `getAppDetail`, `getStoreInfo` — all
`Not supported api`.

## `tvinfo`

`{api: 'initialData'}` returns the device's status snapshot:

```json
{"ret":true,"msg":{"tvLogo":"his","tvBrand":"Hisense","modelName":"65Q60SEVS_01",
 "softwareVersion":"V0000.09.60V.Q0612","chipsetName":"MTK9603","region":"EU_A",
 "4kState":1},"code":0}
```

(device ID and capability/feature codes are present on a live device and have
been redacted here.)

This is the SDK's own first call — `session_array[0]` holds exactly this
request — so it is the cheapest way to confirm that the bridge is alive.
