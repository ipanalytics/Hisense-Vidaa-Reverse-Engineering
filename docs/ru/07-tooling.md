# 7. Инструменты

## Страницы проб

В `tools/` лежат десять HTML-страниц. Каждая — один самодостаточный файл,
который открывается в браузере телевизора и отправляет свои находки на тот
сервер, откуда пришёл. Ни одна не пишет на устройство: только `fileRead`,
`getOSVersion`, `getVersionStatus`, `deviceCode`, `getInstalledPkgs` и
`tvinfo.initialData`.

| Страница | Что проверяет |
|---|---|
| `p.html` | окружение: какие глобалы есть, жив ли мост, девять форм аргумента `fileRead` |
| `p2.html` | десять имён корневого ключа, при удаче — сразу пачка файлов |
| `p3.html` | 45 имён-кандидатов с меткой, формы-массивы, исходники обёрток, чтения tvinfo |
| `p4.html` | поиск служб, 70 имён api у `hiutils`, обход каталога, ресурсы страницы |
| `p5.html` | внутренности службы (`identifier`, `session`, `port`, `httpOption`), ещё 40 имён служб |
| `p6.html` | попытки регистрации, `tvinfo/initialData`, исходники протокола |
| `p7.html` | подмена идентичности через `vowOSContext` (первая, неполная попытка) |
| `p8.html` | то же плюс `navigator.appIdentifier` |
| `p9.html` | оригинальный `vowOSContext`, метаданные `pkgmgr`, исходники `execute()` |
| `p10.html` | `getAppId()`, значение из `init()`, оба транспорта с идентичностями |

Страницы написаны так, что адрес collector'а не задан явно: все запросы
относительные, к тому же хосту, который отдал страницу. Поэтому их можно
положить на любой локальный сервер, не переписывая. Опорный сервер во время
исследования принимал `/probe` и `/upload` и складывал JSON — они лежат в
`samples/`.

### Как запустить

```bash
python3 -m http.server 8090 --bind 0.0.0.0
```

Дальше в браузере телевизора открыть `http://<адрес сервера>:8090/p.html`.
Результаты придут POST-запросами.

## Чем разбиралась прошивка

Энтропия и поиск сигнатур:

```bash
python3 - <<'PY'
import collections, math
d = open('MstarUpgrade.bin','rb').read()
body = d[0x1000:0x1000+4*1024*1024]
c = collections.Counter(body); n = len(body)
print(-sum(v/n*math.log2(v/n) for v in c.values()))
PY
```

Проверка на ECB — считать повторы 16-байтных блоков: ноль повторов означает
CBC/CTR/XTS и делает атаку по словарю бессмысленной.

`epk2extract` собирается, но этот контейнер не увидит — он держит в репозитории
для справки, чтобы было видно, по какому магику он ищет:

```bash
git clone https://github.com/openlgtv/epk2extract
cd epk2extract && ./build.sh        # нужны cmake, libssl-dev, liblzo2-dev, zlib1g-dev
```

REA для работы с прошивкой требует абсолютного пути в `REA_BINWALK_COMMAND`:

```bash
export GHIDRA_INSTALL_DIR=… JAVA_HOME=…
rea doctor --provider ghidra --json
rea inspect-firmware-regions MstarUpgrade.bin
```

## Мелочь про браузер

Телевизор рисует страницы Chromium 111 на ARMv7 и подменяет токен в
User-Agent в зависимости от контекста: `SurfMaster/6.1.8`, `PageReader/8.3.8`,
`ViewPort/8.3.5`. Разные токены в двух запусках — это нормально, а не другой
браузер.
