# 7. Tooling

**Русская версия: [docs/ru/07-tooling.md](ru/07-tooling.md)**

## Probe pages (`tools/`)

Ten HTML pages, each one a single self-contained file that runs on the TV and
POSTs its findings back to the server that served it. They only ever call read
APIs — `fileRead`, `getOSVersion`, `getVersionStatus`, `deviceCode`,
`getInstalledPkgs`, `tvinfo.initialData`. No `fileWrite`, no `installApp`, no
uninstall.

| Page | Purpose |
|---|---|
| `p.html` | environment: which vendor globals exist, does the bridge answer, nine `fileRead` argument shapes |
| `p2.html` | ten root-key candidates for `fileRead`, then a batch read if one wins |
| `p3.html` | 45 marker-carrying argument keys, array forms, wrapper sources, tvinfo reads |
| `p4.html` | local service discovery, 70 `hiutils` api names, traversal, page resources |
| `p5.html` | service internals (`identifier`, `session`, `port`, `httpOption`), 40 more service names |
| `p6.html` | registration attempts, `tvinfo/initialData`, protocol sources |
| `p7.html` | identity injection through `vowOSContext` (first attempt, incomplete) |
| `p8.html` | identity injection including `navigator.appIdentifier` |
| `p9.html` | original `vowOSContext`, `pkgmgr` metadata APIs, `execute()` sources |
| `p10.html` | `getAppId()`, `init()` return value, both transports with identifiers |

### Serving them

`tools/server.py` is the collector used during the research: it serves the pages,
hands out the path queue on `/job`, and stores whatever the TV posts to `/probe`
and `/upload` under `dumps/`.

```bash
python3 tools/server.py --port 8090 --http
```

Open `http://<server>:8090/p.html` in the TV's browser.

Behaviour is pinned by `tools/test_server.py` (stdlib `unittest`, no network
access, nine tests):

```bash
cd tools && python3 -m unittest test_server
```

Any other static server works too if you only need the pages — `python3 -m http.server 8090` — but then results are not collected.

The pages derive the collector URL from nothing but relative paths, so they work
unchanged on any host. **Do not hardcode your own address before publishing.**

## Analysis tooling used on the firmware

```bash
# entropy / signature survey
python3 - <<'PY'
import collections, math
d = open('MstarUpgrade.bin','rb').read()
body = d[0x1000:0x1000+4*1024*1024]
c = collections.Counter(body); n = len(body)
print(-sum(v/n*math.log2(v/n) for v in c.values()))
PY

# block-reuse test (ECB detector): 0 repeats => not ECB
```

```bash
# epk2extract (will not detect this container; kept for reference)
git clone https://github.com/openlgtv/epk2extract
cd epk2extract && ./build.sh        # needs cmake, libssl-dev, liblzo2-dev, zlib1g-dev
```

```bash
# REA (needs an absolute REA_BINWALK_COMMAND for any firmware command)
export GHIDRA_INSTALL_DIR=… JAVA_HOME=…
rea doctor --provider ghidra --json
rea inspect-firmware-regions MstarUpgrade.bin
```

## A note on the browser

The TV renders pages with Chromium 111 on ARMv7 and swaps the UA token by
context: `SurfMaster/6.1.8`, `PageReader/8.3.8`, `ViewPort/8.3.5`. Seeing a
different token between two runs is normal and does not indicate a different
browser.
