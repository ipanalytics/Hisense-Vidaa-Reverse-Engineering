# 2. Локальные службы телевизора

Второй слой устройства — это то, что работает внутри самого телевизора и
отвечает веб-страницам. Найти его было просто: в исходниках обёрток `vowOS`
лежит готовая строка подключения.

```js
function sendPkgmgrRequest(api, args, appinfo, callback) {
    const encodedData = encodeURIComponent(JSON.stringify(args));
    const url = `https://localhost:9888/service/pkgmgr?api=${api}&args=${encodedData}`;
```

Отсюда два факта. Первый: внутри телевизора есть HTTP-служба на порту 9888.
Второй: она принимает имя службы прямо в пути, то есть `pkgmgr` — не
единственная. Дальше оставалось проверить, какие имена она знает.

Снаружи порт закрыт: с соседней машины в той же подсети `9888` не отвечает,
хотя сам телевизор пингуется за 1,4 мс и держит открытым `36669` — это его
MQTT для приложения-пульта. Значит служба слушает только `localhost`, и
добраться до неё можно лишь изнутри телевизора, то есть из страницы, которую
он сам отрисовал.

## Какие службы существуют

Перебор пятидесяти четырёх правдоподобных имён дал ровно три ответа с кодом
200: `pkgmgr`, `hiutils`, `tvinfo`. Всё остальное — `file`, `files`, `tvapi`,
`appconfig`, `system`, `upgrade`, `ota`, `debug`, `shell`, `exec`, `log`,
`network`, `settings`, `storage`, `cert`, `factory`, `hotel`, `usb`,
`screenshot` и прочие — отвечает одинаково:

```json
{"ret":false,"msg":"Wrong request:/service/<name>?api=...","code":500,"sdkVersion":"1.5.0"}
```

Корень `https://localhost:9888/` отвечает `service register failed` с кодом
503, то есть это точка регистрации, а не оглавление. Оглавления нет нигде:
служба не рассказывает о себе, её приходится опрашивать.

## Почему это вообще доступно странице

Ответы приходят с разрешающей политикой CORS. Иначе говоря, документ,
отданный с любого хоста в сети, может прочитать JSON от `localhost:9888`.
Именно так и собирался весь инвентарь ниже: страница на нашем сервере,
открытая в браузере телевизора, дёргала службу и отправляла ответы обратно.

С POST-запросами из обычного `XMLHttpRequest` так не выходит: служба не
отвечает на `OPTIONS`, и префлайт обрывает запрос. Поэтому штатный SDK ходит
синхронным XHR и websocket-каналом — об этом в
[третьем документе](03-phoenix-protocol.md).

## `hiutils` — то, ради чего всё затевалось

Эта служба проверяет имя api по белому списку и на всё незнакомое отвечает
`{"ret":false,"msg":"Not supported api","code":500}`. Из примерно семидесяти
испробованных имён существуют шесть:

| api | Что отвечает странице, не являющейся приложением |
|---|---|
| `getOSVersion` | `{"ret":true,"msg":"U09.60"}` |
| `getVersionStatus` | `{"ret":true,"msg":"release"}` |
| `fileRead` | принят (`code 0`), но путь не разрешается |
| `fileWrite` | `503 client request permission check error, please check appconfig` |
| `deviceCode` | `503`, та же ошибка |
| `uninstallApp` | `503`, та же ошибка |

Здесь важны две вещи. Во-первых, проверка прав — это **отдельный, более
поздний** шаг, чем проверка имени api. `fileWrite` существует, он в белом
списке, и отказывает ему не список имён, а слой прав. Во-вторых, `fileRead`
через этот слой проходит: чтение сочли недостаточно чувствительным, чтобы его
запирать.

### Как `fileRead` собирает путь

```js
HiUtils_createRequest('fileRead', { path: '/etc/passwd' })
→ {"ret":false,"msg":{"errno":-2,"code":"ENOENT","syscall":"open",
                     "path":"undefined/etc/passwd"},"code":0}
```

Служба склеивает **корень, зависящий от вызывающего**, с тем, что мы передали
в `args.path`. Для страницы, которая не является установленным приложением,
этот корень вычисляется как `undefined` — и получается `undefined/etc/passwd`.
Файла с таким именем нет, отсюда `ENOENT`.

Проверялось, не передаётся ли корень аргументом: сорок пять имён-кандидатов
(`dir`, `root`, `base`, `baseDir`, `folder`, `prefix`, `pre`, `head`, `mnt`,
`mount`, `mountPoint`, `dev`, `device`, `part`, `partition`, `cwd`, `home`,
`volume`, `disk`, `fs`, `file`, `fileName`, `file_path`, `name`, `id`, `type`,
`sub`, `parent`, `from`, `url`, `src`, `uri`, `location`, `folderPath`,
`pathPrefix`, `path_head`, `mountDir`, `target`, `referer`, `origin`,
`appPath`, `sysPath`, `fileDir`, `rootPath`, `rootDir`, `basePath`) с меткой
внутри значения. Ни одно не подменило префикс. Значит корень берётся не из
аргументов, и подбор имён здесь бессмысленен.

Обход каталога закрыт отдельной проверкой ещё до системного вызова:

```
../../../../etc/version        → "invalid path:../../../../etc/version"
/../../etc/version             → "invalid path:/../../etc/version"
APPS:pkgs/../../etc/version    → "invalid path:APPS:pkgs/../../etc/version"
..%2f..%2f..%2fetc/version     → ENOENT на "undefined..%2f..%2f..%2fetc/version" (не декодируется)
```

То есть `..` не проходит и в процентном виде тоже: строка не декодируется
перед проверкой, поэтому попытка упирается в то же `undefined`.

## `pkgmgr`

Работает только `getInstalledPkgs`. Ответ — настоящий список пакетов, и он
попутно раскрывает, как платформа называет файловые системы:

```json
{"ret":true,"msg":[
  {"name":"tv.vidaa.app.browser","version":"9.6.0-r20260612v",
   "status":"install user installed","type":"ns",
   "path":"APPS:pkgs/tv.vidaa.app.browser/CHA/"},
  {"name":"tv.vidaa.res.iot","version":"1.0.1-r20260612v","type":"res",
   "path":"APPS:pkgs/tv.vidaa.res.iot/…"}
]}
```

Префиксы вида `APPS:` — это виртуальные точки монтирования, а не пути Unix.
Полезно знать, если когда-нибудь дойдёт до чтения файлов: `fileRead`, скорее
всего, тоже работает в пространстве таких префиксов.

Остальные имена, которые просились у этой службы, — `getAppInfo`,
`getAppConfig`, `getPermissions`, `getAppList`, `getPkgInfo`, `getStartupApps`,
`getRunningApps`, `getAppDetail`, `getStoreInfo` — все ответили `Not supported api`.
То есть метаданных приложений, включая вожделенный `appconfig`, снаружи не
видно.

## `tvinfo`

Запрос `{api: 'initialData'}` возвращает снимок состояния устройства:

```json
{"ret":true,"msg":{"tvLogo":"his","tvBrand":"Hisense","modelName":"65Q60SEVS_01",
 "softwareVersion":"V0000.09.60V.Q0612","chipsetName":"MTK9603","region":"EU_A",
 "4kState":1},"code":0}
```

На живом устройстве там же приходят device ID, capability- и feature-коды — в
этом репозитории они вырезаны.

Это первый запрос, который делает сам SDK при загрузке страницы: в
`session_array[0]` лежит именно он. Поэтому `initialData` — самый дешёвый
способ проверить, что мост жив и отвечает, прежде чем лезть дальше.
