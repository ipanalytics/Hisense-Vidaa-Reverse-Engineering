# 8. Карта функций по прошивкам

**English version: [docs/08-function-map.md](../08-function-map.md)**

Набор функций моста не одинаков в разных поколениях VIDAA, и это, пожалуй,
самый полезный артефакт здесь: по нему видно, что новая сборка забирает и что
добавляет.

## Метод

Два инвентаря, сравнение по именам:

1. **Это устройство** — 96 имён, собранных обходом `window` на странице,
   которую отрисовал сам телевизор, плюс `Function.prototype.toString()` для
   каждой. Ничего не угадано: список — это то, что прошивка действительно
   выставляет.
2. **Эталонная библиотека** — 113 различных имён `Hisense_*` в том виде, в
   каком их использует публичный проект `vidaa-edge`, рассчитанный на более
   старые сборки VIDAA.

Сравнение без учёта регистра, потому что имена разъезжались с обеих сторон
(`GetTvLogo` против `GetTVLogo`, `GetWoWEnable` против `GetWOWEnable`,
`GetMenuTransparency` против `GetMenuTransparecy` и так далее). Итог: 41 имя
есть в эталоне и отсутствует здесь, 23 есть здесь и отсутствуют в эталоне.

## 41 имя, исчезнувшее в этой сборке

Сгруппировано по тому, что раньше позволяло:

**Файлы и приложения**

```
Hisense_FileRead          Hisense_FileWrite
Hisense_installApp        Hisense_installApp_V2
Hisense_uninstallApp      Hisense_getInstalledApps
```

**Сервисные коды и криптография**

```
Hisense_CheckCodeValid    Hisense_CheckAccessCode
Hisense_Encrypt           Hisense_Decrypt          Hisense_RSADecrypt
Hisense_HiSdkSignCreate   Hisense_HiSdkSignCreateSoundbar
Hisense_HiSdkJsonVerifyHeap
```

**Отладка**

```
Hisense_getDebugPort      Hisense_setDebugPort
Hisense_EnableDebugLog    Hisense_GetDebugLevelForHisenseUI
Hisense_PrintLogMessage   Hisense_WriteTvRunLog
Hisense_GetTestApiList
```

**Сеть**

```
Hisense_GetDNS            Hisense_SetDNS
Hisense_GetMacAddress     Hisense_GetUpdatesVerInfo
Hisense_ResetDevice
```

**Идентичность, рейтинги, картинка**

```
Hisense_GetCustomerID     Hisense_SetCustomerID
Hisense_GetRoleID         Hisense_SetRoleID
Hisense_GetMovieRating    Hisense_GetTvRating
Hisense_GetTvChildrenRating  Hisense_GetCanEngRating  Hisense_GetCanFreRating
Hisense_GetRatingEnable   Hisense_GetParentControls  Hisense_GetParentalControlEnabled
Hisense_GetPictureModeList   Hisense_SetPictureMode
```

## 23 имени, которые есть только здесь

```
Hisense_GetArcMode            Hisense_GetAudioFormat       Hisense_GetAudioMode
Hisense_GetCCAtvChannel       Hisense_GetCCAtvSupport      Hisense_GetCCDtvService
Hisense_GetDatePattern        Hisense_GetDtvStandard       Hisense_GetFaderMode
Hisense_GetMagnification      Hisense_GetMagnificationEnable
Hisense_GetMenuTransparecy    Hisense_GetPrimarySubtitle   Hisense_GetSecondarySubtitle
Hisense_GetSubtitleMode       Hisense_GetSubtitleStorage   Hisense_GetSubtitleStyle
Hisense_GetSupportTTS         Hisense_GetTTSFocusAudio     Hisense_GetTTSSupportLanguage
Hisense_GetTunerSupport       Hisense_RegisterVolumeObserver   Hisense_SetVolume
```

Все добавления — геттеры про доступность, субтитры, тюнер и детали звука.
Платформа росла вширь, а не вглубь.

## Что говорит карта

Интересна не цифра, а форма среза. Исчезло всё, что касалось файлов, сервисных
кодов, криптографии, отладки и установки; осталось всё, что нужно интерфейсу,
чтобы нарисовать меню настроек.

Это согласуется с тем, что независимо показали службы: привилегированная
поверхность не исчезла, она переехала за проверку прав `appconfig` в `hiutils`.
`fileWrite` и `uninstallApp` остались в белом списке и отвечают `503`, то есть
их не удалили — их перестали выдавать непривилегированному вызывающему.

Тот, кто будет сравнивать старый дамп с `vidaa-edge`, должен ожидать ровно
такой разницы по именам: JS-слой — это место, где вендор меняет поведение
между сборками, и измерить это дешево.
