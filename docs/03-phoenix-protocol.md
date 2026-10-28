# 3. The `phoenix://` bridge protocol

**Русская версия: [docs/ru/03-phoenix-protocol.md](ru/03-phoenix-protocol.md)**

The vendor SDK shipped into the TV's web layer speaks a small message protocol
over a WebSocket, with an HTTP fallback that uses the same body shape.

## Message format

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

- `path` — `phoenix://service/<name>`; the scheme prefix is mandatory.
- `method` — `callAPI` for API calls. The SDK also knows `register` (see below).
- `parameters.api` — required. `execute()` rejects a message without it:
  `wrong parameter, should set api or args!` and returns `false` before sending.
- `session` — incremented per call; the reply echoes it so callbacks can be
  matched (`window.vowOS.service.session_array[session]`).
- `timeout` — seconds, default 10 in `execute()`, 2 for the initial call.
- `identifier` — caller identity, filled from `getIdentifier()` (see
  `04-identity-gate.md`).

## Two transports

**WebSocket (primary).** `execute(module, params)` lazily opens
`wss://localhost:9888`. While the socket is not `OPEN`, messages are queued in
`service.msgs` and flushed in `socketonopen`. On each message the SDK looks up
`session_array[session]` and dispatches `onSuccess` / `onError` / `onComplete`,
or `onMessage` when the payload carries `event`. Sessions are deleted after the
reply unless the method was `register` — i.e. **registered sessions are
persistent**, everything else is one-shot.

**HTTP (fallback).** `syncExecute(service, args)` posts the same JSON body to
`https://localhost:9888/service/<name>` using a *synchronous* XHR
(`open('POST', url, false)`) and sets the caller identity as a header:

```js
this.httpRequest.open('POST', url, false)
this.httpRequest.setRequestHeader('identifier', this.getIdentifier())
this.httpRequest.send(JSON.stringify(args))
```

The port pair it probes is:

```js
['https://localhost:9888/service/', 'http://localhost:9009/service/']
```

`9009` is the plain-HTTP alternative; only `9888` answered on the test device.

Attempting the same POST from a normal page fails at CORS preflight — the
service does not answer `OPTIONS`. The SDK sidesteps this because a
synchronous XHR from the same local origin never gets preflighted in the same
way; replicating it with async `fetch` does not work.

## Observable replies

```json
{"ret":true,"msg":{...},"sdkVersion":"1.5.0","code":0}
{"ret":false,"msg":"Not supported api","code":500,"sdkVersion":"1.5.0"}
{"ret":false,"msg":"client request permission check error, please check appconfig","code":503,"sdkVersion":"1.5.0"}
{"ret":false,"msg":"Wrong request:/service/<name>?api=...","code":500,"sdkVersion":"1.5.0"}
{"ret":false,"msg":"invalid path:<path>","sdkVersion":"1.5.0","code":0}
```

`session` is echoed by the service and stripped by the SDK before returning to
the caller (`processResponse` deletes it).

## Watchdog behaviour

If both transports fail twice in a row, the SDK calls `reLaunchService()`,
which sends `{"type":"restartWebsocket"}` through the platform message channel
and retries after five seconds. Worth knowing before poking the socket: a
crashed probe page can leave the service in a restart loop until the next
navigation.
