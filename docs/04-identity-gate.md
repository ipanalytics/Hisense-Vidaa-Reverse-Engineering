# 4. The identity / appconfig gate

Everything privileged on this firmware is refused with one sentence:

```json
{"ret":false,"msg":"client request permission check error, please check appconfig","code":503}
```

That message pinned down the design: the service does not check *what* is
called, it checks *who* is calling, against a per-application configuration
(`appconfig`) that ships with installed applications.

## Where the identity comes from

`vowOS.service.getIdentifier()`:

```js
function() {
    if(window.navigator.appIdentifier !== 'undefined' &&
       window.vowOSContext &&
       typeof(window.vowOSContext?.getAppIdentifier) === 'function') {
        return window.vowOSContext.getAppIdentifier()
    }
    return ''
}
```

On a plain web page in the TV browser the native context exists but is inert:

```
vowOSContext = { init, getAppIdentifier, getAppId }   // all [native code]
getAppIdentifier() -> ""
getAppId()         -> ""
init()             -> "-1"
navigator.appIdentifier -> getter on Navigator.prototype, returns undefined
```

`init()` returning `-1` is the whole story: the page is not running as an
installed application, so the native layer never binds an app identity, and
every later permission check has nothing to look up.

## What can and cannot be forged

Overriding `navigator.appIdentifier` works (an own-property getter on the
`navigator` instance takes precedence over the prototype getter), and replacing
`window.vowOSContext` with a stub makes `getIdentifier()` return any string —
verified: `getIdentifier()` returned `ZQTEST` after the override.

It changes nothing:

| Identity injected | `deviceCode` over HTTP | `deviceCode` over WS | `fileRead` root |
|---|---|---|---|
| `tv.vidaa.app.browser` | 503 | 503 | `undefined` |
| `tv.vidaa.res.iot` | 503 | 503 | `undefined` |
| `system`, `root`, `vidaa`, `hisense` | 503 | 503 | `undefined` |
| `""` | 503 | 503 | `undefined` |

So the `identifier` string in the message body / header is not trusted by
itself. Either the service validates it against a registration it performed
earlier through the native layer, or it ignores it entirely and keys off the
process/session context that the SDK cannot reach from JS.

Two further attempts, both negative:

- `execute('phoenix://service/hiutils', {method:'register', …})` is impossible
  through the SDK: `execute()` requires `parameters.api` and returns `false`
  before any bytes are sent. Opening a **raw** `wss://localhost:9888` and sending
  the same body by hand does reach the service, and `register` is accepted there:

  ```
  session 9002  register + api=getOSVersion    -> {"msg":"registered","code":0}
  session 9004  register + api=initialData     -> {"msg":"registered","code":0}
  session 9003  register + api=deviceCode      -> 503 appconfig
  session 9001  callAPI  + api=deviceCode      -> 503 appconfig
  ```

  So registration exists and sticks (the SDK keeps such sessions alive), but it
  does not grant anything: registering a privileged API returns the same 503 as
  calling it. The identity gate is not bypassed by protocol state.
- `GET https://localhost:9888/` → `service register failed` — the registration
  endpoint exists but refuses unauthenticated calls.

## Why this is the end of the web road

The gate is not a bug that can be typed around: the app identity is established
natively at document creation time, before any JavaScript runs. A page cannot
promote itself into an application, and there is no JS-visible API that grants
permissions.

The only two ways past it are therefore outside the browser:

1. get a document rendered **as an installed application** (the vendor's own
   `hisense://debug` handler installs HTML5 apps on older firmware; on this
   revision the install APIs themselves answer 503, so that door is closed
   from inside), or
2. run code outside the web layer entirely — bootloader/UART.

Both are device-side operations, not protocol tricks.
