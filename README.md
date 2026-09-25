# 📖 Persisch-Deutsches Wörterbuch – Datenpipeline

Zwei aufeinander aufbauende Python-Skripte, die aus einem deutschen Wiktionary-Dump ein KI-übersetztes Deutsch-Persisch-Wörterbuch erzeugen.

`wiktionary_extractor.py` → `wiktionary_raw.json` → `translate_wiktionary_ai.py` → `wiktionary_translated.json`

---

## 🇩🇪 Deutsch

### Überblick

Diese Pipeline besteht aus zwei Schritten:

1. **Extraktion** (`wiktionary_extractor.py`)
   Liest einen deutschen Wiktionary-XML-Dump (auch als `.bz2`) per Streaming ein, erkennt deutsche Wörter anhand des `{{Sprache|Deutsch}}`-Markers und extrahiert Wortart, Bedeutungen, Beispielsätze und Redewendungen. Das Ergebnis wird direkt als JSON-Array in eine Datei geschrieben – ohne den gesamten Dump im Arbeitsspeicher zu halten.

2. **KI-Übersetzung** (`translate_wiktionary_ai.py`)
   Liest die erzeugte JSON-Datei ebenfalls im Streaming-Verfahren, bündelt die Einträge in Batches und schickt sie an die Gemini-API. Das Modell liefert für jedes Wort eine persische Übersetzung, ein Sprachniveau (A1–C2), eine thematische Kategorie und übersetzte Beispielsätze zurück. Der Fortschritt wird gespeichert, sodass ein Abbruch jederzeit fortgesetzt werden kann.

### Funktionsweise (Kurzfassung)

- Beide Skripte arbeiten **speicherschonend** (Streaming statt vollständigem Laden), damit auch sehr große Dumps (mehrere GB) verarbeitet werden können.
- Bereits verarbeitete Wörter werden in einer Fortschrittsdatei vermerkt – bei erneutem Start werden sie übersprungen.
- Fehlgeschlagene Batches werden protokolliert (`failed_batches.log`) statt den ganzen Lauf abzubrechen.

### Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install requests json_repair
```

### Nutzung

**1. Wörter aus dem Wiktionary-Dump extrahieren**

Den aktuellen Dump (z. B. `dewiktionary-latest-pages-articles.xml.bz2`) von [dumps.wikimedia.org](https://dumps.wikimedia.org/dewiktionary/) herunterladen, dann:

```bash
python3 wiktionary_extractor.py dewiktionary-latest-pages-articles.xml.bz2 wiktionary_raw.json
```

**2. Einträge per KI ins Persische übersetzen**

```bash
export GEMINI_API_KEY="dein_api_schluessel"
python3 translate_wiktionary_ai.py
```

Das Skript liest automatisch `wiktionary_raw.json` und schreibt fortlaufend nach `wiktionary_translated.json`.

### Einsatz auf einem Server

Für sehr große Dumps empfiehlt sich der Betrieb in einer `screen`- oder `tmux`-Sitzung bzw. als `systemd`-Dienst, damit der Prozess auch nach Verbindungsabbruch weiterläuft:

```bash
tmux new -s wiktionary
python3 wiktionary_extractor.py dump.xml.bz2 wiktionary_raw.json
# Strg+B, D zum Trennen; tmux attach -t wiktionary zum Wiederverbinden
```

### Lizenz & Datenquelle

Die Rohdaten stammen aus dem [deutschen Wiktionary](https://de.wiktionary.org) und stehen unter **CC BY-SA**. Bei Veröffentlichung muss diese Lizenz und Quelle genannt werden.

---

## 🇮🇷 فارسی

### معرفی کلی

این پروژه شامل دو اسکریپت پایتون است که به‌ترتیب روی هم کار می‌کنند:

1. **استخراج داده‌ها** (`wiktionary_extractor.py`)
   یک فایل XML از Wiktionary آلمانی (حتی به‌صورت فشرده `.bz2`) را به‌صورت استریم می‌خواند، واژه‌های آلمانی را با نشانه‌ی `{{Sprache|Deutsch}}` تشخیص می‌دهد و نوع واژه، معانی، مثال‌ها و اصطلاحات مرتبط را استخراج می‌کند. خروجی مستقیماً در قالب یک آرایه‌ی JSON روی دیسک نوشته می‌شود، بدون اینکه کل فایل در حافظه بارگذاری شود.

2. **ترجمه با هوش مصنوعی** (`translate_wiktionary_ai.py`)
   فایل JSON تولیدشده را نیز به‌صورت استریم می‌خواند، واژه‌ها را در دسته‌های کوچک گروه‌بندی می‌کند و به Gemini API می‌فرستد. مدل برای هر واژه ترجمه‌ی فارسی، سطح زبانی (A1 تا C2)، دسته‌بندی موضوعی و ترجمه‌ی مثال‌ها را برمی‌گرداند. پیشرفت کار ذخیره می‌شود تا در صورت قطع‌شدن، ادامه‌ی کار از همان‌جا ممکن باشد.

### روند کلی کار

- هر دو اسکریپت به‌صورت **کم‌مصرف از نظر حافظه** طراحی شده‌اند تا فایل‌های چند گیگابایتی هم بدون مشکل پردازش شوند.
- واژه‌های پردازش‌شده در یک فایل پیشرفت ثبت می‌شوند و در اجرای بعدی دوباره پردازش نمی‌شوند.
- دسته‌های ناموفق در فایل `failed_batches.log` ثبت می‌شوند تا کل فرایند متوقف نشود.

### نصب

```bash
python3 -m venv venv
source venv/bin/activate
pip install requests json_repair
```

### نحوه‌ی استفاده

**۱. استخراج واژه‌ها از فایل Wiktionary**

ابتدا آخرین نسخه‌ی dump (مثلاً `dewiktionary-latest-pages-articles.xml.bz2`) را از [dumps.wikimedia.org](https://dumps.wikimedia.org/dewiktionary/) دانلود کنید، سپس:

```bash
python3 wiktionary_extractor.py dewiktionary-latest-pages-articles.xml.bz2 wiktionary_raw.json
```

**۲. ترجمه‌ی واژه‌ها به فارسی با هوش مصنوعی**

```bash
export GEMINI_API_KEY="کلید_ای‌پی‌آی_شما"
python3 translate_wiktionary_ai.py
```

این اسکریپت به‌طور خودکار فایل `wiktionary_raw.json` را می‌خواند و خروجی را پیوسته در `wiktionary_translated.json` می‌نویسد.

### اجرا روی سرور

برای فایل‌های بسیار بزرگ، بهتر است اسکریپت در یک نشست `screen` یا `tmux`، یا به‌عنوان یک سرویس `systemd` اجرا شود تا حتی بعد از قطع اتصال هم به کار خود ادامه دهد:

```bash
tmux new -s wiktionary
python3 wiktionary_extractor.py dump.xml.bz2 wiktionary_raw.json
# Ctrl+B سپس D برای جدا شدن؛ tmux attach -t wiktionary برای اتصال دوباره
```

### مجوز و منبع داده

داده‌های خام از [Wiktionary آلمانی](https://de.wiktionary.org) گرفته شده‌اند و تحت مجوز **CC BY-SA** منتشر می‌شوند. در صورت انتشار پروژه، ذکر این مجوز و منبع الزامی است.
