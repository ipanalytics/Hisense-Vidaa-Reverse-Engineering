# 3. Протокол моста `phoenix://`

**English version: [docs/03-phoenix-protocol.md](../03-phoenix-protocol.md)**

Служба на порту 9888 говорит не «URL плюс параметры», а короткими сообщениями
со схемой `phoenix://`. Схему и формат удалось прочитать целиком: обёртки в
веб-слое написаны на обычном JavaScript, поэтому `Function.prototype.toString()`
отдаёт их исходники без всякой декомпиляции.

## Формат сообщения

```json
{
  "path": "phoenix://service/tvinfo",
  "method": "callAPI",
  "parameters": { "api": "initialData", "args": "" },
  "session": 0,
  "timeout": 2,
  "identifier": ""
}
```

Разберём поля по смыслу.

`path` — адрес службы в виде `phoenix://service/<имя>`. Префикс обязателен:
без него SDK ругается в консоль, хотя сообщение всё равно отправит.

`method` — `callAPI` для обычного вызова. В коде есть ещё ветка `register`,
но пройти в неё из страницы нельзя, и об этом ниже.

`parameters` — объект с обязательным полем `api`. Если его нет, `execute()`
пишет `wrong parameter, should set api or args!` и возвращает `false` ещё до
отправки — то есть сообщение вообще не уходит.

`session` — счётчик, который увеличивается на каждый вызов. Ответ приходит с
тем же номером, и по нему SDK находит колбэки в
`window.vowOS.service.session_array[session]`. После ответа сессия удаляется,
кроме случая, когда метод был `register`: зарегистрированные сессии живут
дольше одного запроса.

`timeout` — секунды. По умолчанию 10 в `execute()` и 2 у первого запроса SDK.

`identifier` — идентичность вызывающего. Как она получается и почему её не
подделать — в [четвёртом документе](04-identity-gate.md).

## Два транспорта

**WebSocket — основной.** `execute(module, params)` при первом вызове
открывает `wss://localhost:9888` и подписывается на четыре события: открытие,
сообщение, закрытие, ошибка. Если сокет ещё не в состоянии `OPEN`, сообщение
кладётся в очередь `service.msgs` и уходит в `socketonopen`. На каждый
входящий пакет SDK смотрит `session_array` и вызывает `onSuccess`, `onError`
или `onComplete`; если в пакете есть поле `event`, вызывается `onMessage` —
так приходят подписки на изменения свойств.

**HTTP — запасной.** `syncExecute(service, args)` отправляет то же тело на
`https://localhost:9888/service/<name>`, причём синхронным запросом:

```js
this.httpRequest.open('POST', url, false)
this.httpRequest.setRequestHeader('identifier', this.getIdentifier())
this.httpRequest.send(JSON.stringify(args))
```

Порты, которые он пробует при инициализации, — пара
`['https://localhost:9888/service/', 'http://localhost:9009/service/']`. На
подопытном телевизоре ответил только `9888`; `9009` остался закрыт.

Повторить это обычным асинхронным запросом не получается: служба не отвечает
на `OPTIONS`, и браузер обрывает вызов на префлайте. Штатный SDK обходит это
синхронным XHR — воспроизводится только так.

## Какие ответы приходят

```json
{"ret":true,"msg":{...},"sdkVersion":"1.5.0","code":0}
{"ret":false,"msg":"Not supported api","code":500,"sdkVersion":"1.5.0"}
{"ret":false,"msg":"client request permission check error, please check appconfig","code":503,"sdkVersion":"1.5.0"}
{"ret":false,"msg":"Wrong request:/service/<name>?api=...","code":500,"sdkVersion":"1.5.0"}
{"ret":false,"msg":"invalid path:<path>","sdkVersion":"1.5.0","code":0}
```

Поле `session` служба возвращает, а SDK его вырезает перед выдачей вызывающему
— в `processResponse` есть `delete ret.session`. Поэтому в ответах, которые
видит страница, номера сессии уже нет.

## Сторож и перезапуск

Если оба транспорта подряд дважды не отвечают, SDK считает службу потерянной
и вызывает `reLaunchService()`. Тот отправляет платформенное сообщение
`{"type":"restartWebsocket"}` и через пять секунд пробует снова. Полезно
помнить, прежде чем дёргать сокет вручную: упавшая страница-проба может
оставить службу в цикле перезапуска до следующей навигации.
