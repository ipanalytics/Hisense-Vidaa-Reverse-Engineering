# 6. Отрицательные результаты

Ниже — всё, что было испробовано и **не сработало**. Этот раздел существует
затем, чтобы следующий человек не тратил на это время: часть попыток выглядит
очевидной, пока не упрёшься.

## Контейнер прошивки

| Попытка | Итог |
|---|---|
| `binwalk -E` и скан сигнатур по первым 128 МиБ | только ложные попадания «JBOOT STAG» |
| Определение `epk2extract` | ни `hise`, ни `#DH@FiRm`, ни `iMtK8` во всех 1 005 336 192 байтах |
| Публичные ключи `epk2extract`: `09291094…`, `53686172…` (Sharp), `5450565F…` (TPV) в ECB, CBC, CTR | печатный мусор, ни одного магика |
| DES-ECB `0123456789ABCDEF`, AES-128-ECB `0123…`, AES-256-ECB, нулевые ключи | то же самое |
| `REA inspect-firmware-regions` и `extract-firmware` | `capability_unavailable`: нужен `REA_BINWALK_COMMAND`, а извлечение всё равно по сигнатурам |
| Проверка на ECB по повторам 16-байтных блоков в 64 МиБ | ноль повторов, значит CBC/CTR/XTS |

## Построение пути в `fileRead`

| Попытка | Итог |
|---|---|
| 45 имён аргумента с меткой (`dir`, `root`, `base`, `baseDir`, `folder`, `prefix`, `pre`, `head`, `mnt`, `mount`, `mountPoint`, `dev`, `device`, `part`, `partition`, `cwd`, `home`, `volume`, `disk`, `fs`, `file`, `fileName`, `file_path`, `name`, `id`, `type`, `sub`, `parent`, `from`, `url`, `src`, `uri`, `location`, `folderPath`, `pathPrefix`, `path_head`, `mountDir`, `target`, `referer`, `origin`, `appPath`, `sysPath`, `fileDir`, `rootPath`, `rootDir`, `basePath`) | префикс остался `undefined`, метка не появилась ни разу |
| Аргумент массивом: `["MARK/", "/etc/version"]`, `["/etc/version"]` | ответ `{}` |
| Аргумент `null`, `{}`, `0` | ответ `{}` |
| Обход `../../../../etc/version`, `/../../etc/version`, `APPS:pkgs/../../…` | `invalid path:<путь>` — отдельная проверка до системного вызова |
| Обход в процентном виде `..%2f..%2f..` | не декодируется, `ENOENT` на `undefined..%2f…` |

## Перебор служб и api

| Попытка | Итог |
|---|---|
| 54 имени служб | отвечают только `pkgmgr`, `hiutils`, `tvinfo` |
| Около 70 имён api у `hiutils` | в белом списке только `fileRead`, `fileWrite`, `deviceCode`, `uninstallApp`, `getVersionStatus`, `getOSVersion` |
| `pkgmgr`: `getAppInfo`, `getAppConfig`, `getPermissions`, `getAppList`, `getPkgInfo`, `getStartupApps`, `getRunningApps`, `getAppDetail`, `getStoreInfo` | `Not supported api` |
| `syncExecute('tvapi', …)` | `false` — службы `tvapi` в веб-слое нет |

## Идентичность

| Попытка | Итог |
|---|---|
| Подмена `vowOSContext.getAppIdentifier` | `getIdentifier()` возвращает подставленное, права не меняются |
| Подмена геттера `navigator.appIdentifier` на объекте | работает на уровне JS, на права не влияет |
| Идентичности `tv.vidaa.app.browser`, `tv.vidaa.res.iot`, `system`, `root`, `vidaa`, `hisense`, `tv.vidaa.app.settings`, `browser`, пустая | `deviceCode` даёт 503 и по HTTP, и по WebSocket во всех случаях |
| `execute(…, {method:'register'})` | невозможно: `execute()` требует `parameters.api` и возвращает `false` до отправки |
| `GET https://localhost:9888/` | `service register failed`, 503 |
| Асинхронный `fetch`/XHR POST на `/service/<name>` | обрывается на CORS-префлайте (`onerror`) |
| `setPkgmgrRequest('installApp')` | сознательно не вызывалось: это запись, вне рамок исследования |

## Что эти отказы означают

Модель прав держится не на JavaScript, поэтому подмена объектов на странице
ничего не даёт. Идентичность приложения привязывается нативно при создании
документа, и страница не может её себе выдать. Прямое подтверждение:
`vowOSContext.init()` возвращает `-1`, `getAppIdentifier()` и `getAppId()` —
пустые строки.
