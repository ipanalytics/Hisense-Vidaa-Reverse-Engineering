# 6. Negative results

Everything below was tried on the test device and **did not work**. Recorded so
the next person does not repeat it.

## Firmware container

| Attempt | Outcome |
|---|---|
| `binwalk -E` / signature scan, first 128 MiB | only false "JBOOT STAG" hits |
| `epk2extract` detection | no `hise` / `#DH@FiRm` / `iMtK8` magic anywhere in 1 005 336 192 bytes |
| `epk2extract` public keys: `09291094…`, `53686172…` (Sharp), `5450565F…` (TPV) in ECB/CBC/CTR | printable garbage, no magic |
| DES-ECB `0123456789ABCDEF`, AES-128-ECB `0123…`, AES-256-ECB, zero keys | garbage |
| REA `inspect-firmware-regions` / `extract-firmware` | `capability_unavailable`: needs `REA_BINWALK_COMMAND`; signature-driven anyway |
| ECB-detection (repeated 16-byte blocks in 64 MiB) | 0 repeats → CBC/CTR/XTS, not ECB |

## `fileRead` path construction

| Attempt | Outcome |
|---|---|
| 45 candidate argument names carrying a marker (`dir`, `root`, `base`, `baseDir`, `folder`, `prefix`, `pre`, `head`, `mnt`, `mount`, `mountPoint`, `dev`, `device`, `part`, `partition`, `cwd`, `home`, `volume`, `disk`, `fs`, `file`, `fileName`, `file_path`, `name`, `id`, `type`, `sub`, `parent`, `from`, `url`, `src`, `uri`, `location`, `folderPath`, `pathPrefix`, `path_head`, `mountDir`, `target`, `referer`, `origin`, `appPath`, `sysPath`, `fileDir`, `rootPath`, `rootDir`, `basePath`) | prefix stayed `undefined`, marker never appeared |
| `args` as array `["MARK/", "/etc/version"]` or `["/etc/version"]` | reply `{}` |
| `args` as `null`, `{}`, `0` | reply `{}` |
| Traversal `../../../../etc/version`, `/../../etc/version`, `APPS:pkgs/../../…` | `invalid path:<path>` — explicit validation before the syscall |
| Percent-encoded traversal `..%2f..%2f..` | not decoded, ENOENT on `undefined..%2f…` |

## Service and API enumeration

| Attempt | Outcome |
|---|---|
| 54 service names | only `pkgmgr`, `hiutils`, `tvinfo` answer 200 |
| ~70 `hiutils` api names | only `fileRead`, `fileWrite`, `deviceCode`, `uninstallApp`, `getVersionStatus`, `getOSVersion` are whitelisted |
| `pkgmgr`: `getAppInfo`, `getAppConfig`, `getPermissions`, `getAppList`, `getPkgInfo`, `getStartupApps`, `getRunningApps`, `getAppDetail`, `getStoreInfo` | `Not supported api` |
| `syncExecute('tvapi', …)` | `false` — no `tvapi` service in the web layer |

## Identity

| Attempt | Outcome |
|---|---|
| Override `vowOSContext.getAppIdentifier` | `getIdentifier()` returns the injected value; permissions unchanged |
| Override `navigator.appIdentifier` (own getter on the instance) | works at JS level; permissions unchanged |
| Identities `tv.vidaa.app.browser`, `tv.vidaa.res.iot`, `system`, `root`, `vidaa`, `hisense`, `tv.vidaa.app.settings`, `browser`, `""` | `deviceCode` 503 on HTTP and on WebSocket for every one |
| `execute(…, {method:'register'})` | impossible: `execute()` requires `parameters.api`, returns `false` before sending |
| `GET https://localhost:9888/` | `service register failed`, 503 |
| Async `fetch`/XHR POST to `/service/<name>` | blocked at CORS preflight (`onerror`) |
| `pkgmgr`: `installApp`, `install`, `installPkg` via the GET form (no preflight) | `Not supported api` — the service has no install API at all, so it is not even permission-gated |

## When the install path disappeared

The removal is not sudden — it has a timeline, partly from other people's
reports and partly confirmed here:

| Build | Web-app install via the debug path |
|---|---|
| `N0519`, `O0904` (2023–2024) | worked; users installed and later had to downgrade to keep the app |
| `P0603` (2025) | gone — `Hisense_installApp` no longer present |
| `Q0612` (2026, this device) | confirmed dead: handler absent, `install`/`uninstallApp` answer 503, 41 of 113 reference `Hisense_*` names removed |

The first two rows are other people's reports; the third was measured on the
device described here. Treat the table as a starting point for a proper
version-by-version map, not as a finished one.

## What the negatives mean

The permission model is not enforced at the JavaScript layer, so no amount of
patching page-side objects helps. The app identity is bound natively when the
document is created; a page cannot acquire one. Confirmation:
`vowOSContext.init()` returns `-1`, `getAppIdentifier()` and `getAppId()` return
empty strings.
