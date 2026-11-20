# 📋 سند ملاحظات فنی و تصمیمات پیش‌رو — Ramz

> **نسخه:** v1.0
> **تاریخ:** 2026-11-20
> **وضعیت:** پیوست رسمی roadmap — قابل استناد در تمام فازهای آینده
> **مرجع همراه:** `initial-review-report`، `Ramz-crypto-roadmap`، `task-prompt.v2.0`

---

## مقدمه

این سند دو دستهٔ محتوا را ثبت می‌کند که در تحلیل تقاطع **Massir 0.2.0 Alpha** و **Ramz** استخراج شده‌اند:

1. **ملاحظات فنی (۶ مورد)** — نقاطی که آگاهانه باید در طراحی ماژول‌های آینده رعایت شوند، حتی اگر امروز اقدام مستقیمی لازم نباشد.
2. **تصمیمات و افق‌های پیش‌رو (A–H)** — پاسخ‌های تأییدشده برای سؤالات کلیدی طراحی، که مرزهای مجاز فازهای بعدی را تعیین می‌کنند.

این سند به‌عنوان **پیوست رسمی roadmap** در نظر گرفته می‌شود و در شروع هر فاز جدید باید مرور شود.

---

# بخش اول — ملاحظات فنی (تأییدشده)

## ۱. Presence Registry در حالت in-memory

**وضعیت فعلی:** `PresenceRegistry` (TTL 90s) در فاز ۱ به‌صورت in-memory پیاده شده است.

**تحلیل:**
- در معماری تک‌سرور + uvicorn تک-worker، این پیاده‌سازی **کافی و صحیح** است.
- در صورت مهاجرت به چند-worker یا چند-سرور (که برای مقیاس لازم خواهد شد)، heartbeat هر کاربر به worker خاصی می‌رود و presence در آن worker محبوس می‌شود — نتیجه: ناسازگاری وضعیت.

**اقدام تعیین‌شده:**
- **الان:** هیچ اقدامی نکنیم.
- **آینده:** `PresenceRegistry` باید **از ابتدا با interface طراحی شود** (مثلاً `BasePresenceRegistry`) تا پیاده‌سازی in-memory و Redis قابل تعویض باشند. این تصمیم در طراحی فاز ۴+ لحاظ شود.

**مرجع:** تصمیم D — انتقال به Redis در آینده ساده باشد.

---

## ۲. جدول `crypto_price_history` — رزرو شده، بدون writer

**وضعیت فعلی:** جدول در schema v11 وجود دارد، ولی هیچ کدی در آن INSERT نمی‌کند ("reserved for future recorder").

**تحلیل:**
- SQLite برای تاریخچه بلندمدت candle (چند میلیون row) مناسب نیست — هم از نظر حجم، هم از نظر کوئری تحلیلی.
- این جدول باید صرفاً برای **hot cache کوتاه‌مدت** (مثلاً آخرین چند ساعت) استفاده شود، یا کاملاً حذف شود.

**اقدام تعیین‌شده:**
- **الان:** بدون تغییر.
- **فاز ۴ (crypto_charts):** recorder واقعی برای candle history طراحی شود — با یکی از گزینه‌های ذخیره‌سازی که در تصمیم A آمده.
- **مرجع:** تصمیم A — Parquet + PyArrow + Zstd به‌عنوان گزینهٔ پیشنهادی (نهایی‌سازی در زمان پیاده‌سازی).

---

## ۳. `fetch_klines` در NobitexProvider — stub

**وضعیت فعلی:** در Phase 1/2، providerها `CAP_KLINES` را اعلام نمی‌کنند و `fetch_klines` در Nobitex **stub** است.

**تحلیل:**
- فاز ۴ (crypto_charts) **بدون دادهٔ کندل معنا ندارد**.
- route `POST /crypto/market/api/klines/{symbol}` از فاز ۱ live است ولی هیچ providerی به آن پاسخ واقعی نمی‌دهد.

**اقدام تعیین‌شده:**
- **پیش‌نیاز قطعی فاز ۴:** پیاده‌سازی واقعی `fetch_klines` در NobitexProvider (و در صورت امکان CoinGecko) + اعلام `CAP_KLINES`.
- این پیاده‌سازی باید **قبل از** شروع TASK 80.3 (کامپوننت `<ramz-chart>`) انجام شود.
- **مرجع:** roadmap فاز ۴.

---

## ۴. Poller polling-based با interval=10s — محدودیت برای real-time

**وضعیت فعلی:** `MarketPoller` با `interval=10s`، `fetch_timeout=8s`. برای snapshot قیمت جاری کافی است.

**تحلیل:**
- برای قیمت جاری (نمایش در لیست coin، dashboard widget): **10s کافی است**.
- برای candle 1-minute با دقت بالا: **10s ناکافی است** (حداقل نرخ 1-2s لازم است یا WebSocket).
- برای ترید لحظه‌ای (فاز ۵+): polling به هیچ وجه کافی نیست — نیاز به WebSocket صرافی.

**اقدام تعیین‌شده:**
- **الان:** بدون تغییر.
- **فاز ۴ (crypto_charts):** min interval poller قابل تنظیم برای candle 1m (پیشنهاد: 5s، نه کمتر، برای احترام به rate limit).
- **فاز ۵ (crypto_trading):** مهاجرت به WebSocket صرافی برای جریان قیمت لحظه‌ای (همان‌طور که در roadmap به "WebSocket real-time (اختیاری)" اشاره شده).
- **مرجع:** roadmap فاز ۵.

---

## ۵. `CoinData.reference_prices` — median برای نمایش، نه ترید

**وضعیت فعلی:** `aggregator` قیمت reference را با **median** بین providerها + FX conversion محاسبه می‌کند.

**تحلیل:**
- median برای **نمایش و مقایسهٔ اسپرد** ایده‌آل است (نویز outlier را حذف می‌کند).
- median برای **ترید** خطرناک است — اسپرد واقعی صرافی مقصد را نشان نمی‌دهد و ممکن است کاربر با قیمتی ترید کند که در صرافی موجود نیست.

**اقدام تعیین‌شده:**
- **در `crypto_trading` (فاز ۵+):** از `provider_prices[exchange_target]` مستقیم استفاده شود، **نه** `reference_prices`.
- `reference_prices` صرفاً برای UI نمایشی (dashboard، لیست، مقایسهٔ اسپرد) باقی بماند.
- این قاعده باید در `docs/crypto-trading.md` صریحاً مستند شود.

---

## ۶. MasterKeyManager — نیاز به ارتقا قبل از ترید واقعی

**وضعیت فعلی:** یک کلید `crypto_credentials.key` (32 bytes) در `{app_dir}/keys/`، auto-created در اولین startup، `chmod 600` روی Unix.

**تحلیل:**
- برای فاز ۲ (فقط ذخیره/خواندن credentials) کافی است.
- برای **ترید واقعی** (پول واقعی کاربر)، الزامات امنیتی به‌مراتب بالاتر است:
  - کلید نباید در فایل‌سیستم کنار کد باشد (بهتر: env / KMS / HashiCorp Vault).
  - Rotation باید پشتیبانی شود (کلید جدید → re-encrypt همهٔ credentials → کلید قدیم حذف).
  - Backup جدا از DB (الان در `.gitignore` است، ولی backup خودکار ندارد).
  - Warning در صورت unsafe permissions فقط log می‌شود، بهتر است در production جلوی startup را بگیرد.

**اقدام تعیین‌شده:**
- **الان:** بدون تغییر.
- **قبل از فاز ۵ (crypto_trading live):** ارتقای MasterKeyManager به سه قابلیت: (الف) خواندن از env با fallback به فایل، (ب) rotation API، (ج) pre-flight check سخت‌گیرانه.
- **Gen 3b (system_settings):** UI برای rotation + backup + restore.
- **مرجع:** roadmap فاز ۵ و Gen 3b، TASK 84.4 (Key rotation).

---

# بخش دوم — تصمیمات و افق‌های پیش‌رو (A–H)

## A) ذخیرهٔ تاریخچه و لاگ — Parquet با PyArrow + Zstd

**تصمیم:**
- **گزینهٔ پیشنهادی مورد تأیید:** Parquet با PyArrow + Zstd (ستونی، فشرده‌سازی 5-10x، قابل کوئری با DuckDB بدون DB server).
- **Partition strategy:** partition-by-time (مثلاً `candles/{canonical}/{quote}/{interval}/YYYY-MM/*.parquet`).
- **محدودیت نگهداری (retention):** در زمان پیاده‌سازی مشخص می‌شود.

**وضعیت:** تصمیم قطعی به **زمان پیاده‌سازی فاز ۴** موکول شد. در طراحی schema فاز ۴ باید به‌گونه‌ای پیش برویم که مهاجرت به Parquet بدون بازکاری ممکن باشد.

**مرجع:** تصمیم A، ملاحظهٔ ۲.

---

## B) شبیه‌سازی ترید — فاز مستقل با roadmap جداگانه

**تصمیم:**
- **Paper trading live** و **Backtesting historical** هر دو پیاده‌سازی خواهند شد.
- این کار **یک توسعهٔ کامل مجزا** است که roadmap مستقل خود را دارد.
- **الان به آن پرداخته نمی‌شود** — نه در فاز ۵، نه در فاز ۶. فاز شبیه‌سازی بعد از تکمیل ترید واقعی (یا موازی با آن در تیم جدا) طراحی می‌شود.

**اثر بر طراحی فعلی:**
- در schema v11+ هیچ جدول paper/backtest **الان** اضافه نکنیم (مگر جدول‌های عمومی که در فاز ترید واقعی هم استفاده می‌شوند).
- در `crypto_trading` (فاز ۵) طراحی interfaceها را طوری انجام دهیم که **paper executor** بتواند بعداً به‌عنوان یک پیاده‌سازی جایگزین اضافه شود (مثلاً `BaseOrderExecutor`).

**مرجع:** پاسخ B.

---

## C) `crypto_trading` — تعویق تا طراحی کامل

**تصمیم:**
- فاز ۵ (crypto_trading) **الان شروع نمی‌شود**.
- هنوز نکات طراحی‌نشده دارد که باید قبل از شروع حل شوند:
  - مدل سفارش (market / limit / stop-loss / take-profit)
  - sandbox vs. live mode و نحوهٔ تفکیک
  - audit trail و rate limiting
  - سطح دسترسی و مجوزها (`crypto.trade.execute` فعلاً به هیچ‌کس تعلق ندارد)
  - مدیریت خطای صرافی و reconciliation
- این فاز پس از **تکمیل فاز ۴ (crypto_charts)** و **Gen 3a (supervision)** دوباره ارزیابی می‌شود.

**اثر بر طراحی فعلی:**
- `crypto.trade.execute` در seed v11 رزرو بماند (بدون grant).
- `crypto_order` / `crypto_trade` tables **الان** ساخته نشوند — در migration v12 در زمان شروع فاز ۵.

**مرجع:** پاسخ C، roadmap فاز ۵.

---

## D) Redis — بدون اقدام، فقط interface-ready

**تصمیم:**
- **الان:** هیچ اقدامی نکنیم — نه Redis نصب، نه code.
- **اصل طراحی:** ماژول‌ها باید طوری طراحی شوند که **انتقال به Redis در آینده ساده باشد**.

**الزامات طراحی (برای رعایت در فاز ۴+):**
- `PresenceRegistry` → طراحی با interface (`BasePresenceRegistry`)
- Rate limiter → interface (`BaseRateLimiter`)
- Cache دیتابیس → interface (`BaseCacheBackend`) — هرچند فعلاً `QueryCache` موجود قابل استفاده است.
- هر state مشترک که بین requestها نگهداری می‌شود → از ابتدا به‌عنوان "قابل انتقال به backend خارجی" در نظر گرفته شود.

**مرجع:** پاسخ D، ملاحظهٔ ۱.

---

## E) کتابخانهٔ چارت — lightweight-charts (TradingView) درون `<ramz-chart>`

**تصمیم:**
- **اولویت اول:** `lightweight-charts` (TradingView) — سبک (~40KB)، Canvas-based، candlestick + line + volume آماده، بدون نیاز به React/Vue.
- **شرط استفاده:** اگر قابل دستکاری و افزودن امکانات سفارشی (اندیکاتورهای overlay، annotations، markers) باشد.
- **Fallback:** اگر محدودیت‌های آن اجازه نداد (مثلاً رسم اندیکاتور سفارشی با سبک خاص)، چارت از ابتدا با Canvas/SVG ساخته می‌شود.

**الزامات پیاده‌سازی (فاز ۴):**
- `<ramz-chart>` به‌عنوان Web Component بومی (مطابق قاعدهٔ بدون framework در UI shell).
- lightweight-charts **داخل** Web Component رندر شود — نه به‌عنوان جایگزین معماری.
- CSS سراسری `style.css` همچنان مرجع است؛ چارت با CSS API خودش (رنگ، فونت) هماهنگ شود.

**مرجع:** پاسخ E، roadmap TASK 80.3.

---

## F) اندیکاتورها — کلاسیک در فاز ۶ + نوآورانه در آینده

**تصمیم:**
- گروهی از اندیکاتورهای **مفید و کلاسیک** در فاز ۶ (crypto_analysis) پیاده‌سازی می‌شوند (SMA/EMA/RSI/MACD/BB/Stochastic/ATR/Ichimoku/Volume Profile و ...).
- اندیکاتورهای **خاص با اهداف مشخص** در آینده طراحی می‌شوند — مستقیماً روی چارت نمایش داده می‌شوند.
- **الان طراحی نمی‌شوند**، ولی **از نظر فنی باید در ذهن بماند**.

**الزامات طراحی فعلی (برای رعایت در فاز ۴):**
- `<ramz-chart>` باید از **overlay layer** برای اندیکاتورهای آینده پشتیبانی کند (نه فقط رندر candle).
- API چارت باید پذیرای `overlay: {type, params, series}` باشد تا افزودن اندیکاتور جدید در آینده بدون تغییر کامپوننت ممکن باشد.
- `docs/crypto-charts.md` (TASK 80.9) باید بخش "Overlay extension points" داشته باشد.

**مرجع:** پاسخ F، roadmap فاز ۶.

---

## G) CoinGecko — free API الان، دو رویکرد بعد از soft launch

**تصمیم:**
- **الان:** فقط APIهای free (CoinGecko free tier، Nobitex public).
- **بعد از soft launch و کاربرگیری:** دو رویکرد موازی مد نظر است:
  1. **خرید APIهای پیشرفته** (CoinGecko Pro، صرافی‌های premium).
  2. **دریافت داده از APIها روی مرورگر کلاینت** (CORS-friendly APIs) + توسعهٔ کد کلاینت برای این کار.

**اثر بر طراحی فعلی:**
- Provider interface (`BaseCryptoProvider`) باید طوری طراحی شده باشد که هم **server-side fetch** (الان) و هم **client-side fetch** (آینده) را پشتیبانی کند.
- به‌ویژه: `provider.name`، `capabilities`، `supported_quotes` باید **در API JSON به فرانت‌اند پاس شوند** تا UI بتواند تصمیم بگیرد کدام provider را client-side صدا بزند.
- `docs/extension-system.md` یا `docs/architecture.md` باید بخش "Client-side provider (future)" داشته باشد.
- route `/crypto/market/api/coins` الان server-side است؛ در آینده نیاز به route "provider manifest" (برای کشف providerها توسط client) خواهد بود.

**مرجع:** پاسخ G.

---

## H) ارزهای پشتیبانی‌شده — گسترش‌پذیر بدون محدودیت

**تصمیم:**
- ارزهای پشتیبانی‌شده **محدود به USDT/USD/RLS نیستند**.
- ارزهای فیات دیگر (EUR, AED, TRY, ...) در آینده اضافه می‌شوند.
- **الان باید در نظر گرفته شود** — یعنی مدل داده و schema نباید به سه ارز فعلی hardcode شوند.

**الزامات طراحی (بازبینی مدل داده در فاز ۳/۴):**
- `CoinData.available_quotes` و `reference_prices` هم‌اکنون `dict[str, Decimal]` هستند — **درست و گسترش‌پذیر**.
- `CoinData.price_dispersion_pct` هم `dict[str, Optional[float]]` — **درست**.
- **بررسی لازم:** آیا `symbol_map` و `provider.supported_quotes` به‌صورت set/dict پیاده شده‌اند یا به سه ارز hardcode شده‌اند؟ اگر hardcode باشد → در فاز ۴ اصلاح شود.
- **جفت‌های crypto/crypto** (مثل BTC/ETH): در `canonical` و `quote` باید مدل چند-سطحی پشتیبانی شود. الان `canonical` تک‌سطح است (`"BTC"`). اگر در آینده بخواهیم `BTC/ETH` را canonical کنیم، باید `CoinData` گسترش یابد. **پیشنهاد:** در فاز ۳/۴ یک کامنت در `types.py` بگذاریم که "canonical پایه واحد است؛ گسترش به جفت در آینده".
- **FX conversion:** `aggregator` الان یک `fx` provider برای USD→RLS دارد. برای ارزهای فیات دیگر، `fx` provider باید گسترش یابد (`base_currency` / `quote_currency` عمومی).
- **retention و نمایش:** UI (لیست coin، dashboard widget) الان `display_currency` را از `{USDT, USD, RLS}` انتخاب می‌کند. در آینده باید گسترش یابد — `coins_settings.html` و `crypto_user_preference` باید `display_currency` را به‌صورت string عمومی نگه دارند (نه enum).

**مرجع:** پاسخ H.

---

# بخش سوم — الزامات طراحی قابل استناد (Checklist)

این چک‌لیست در شروع هر فاز جدید باید مرور شود:

| # | الزام | فاز اثرگذار | وضعیت |
|---|---|---|---|
| 1 | `PresenceRegistry` → interface-based برای انتقال آینده به Redis | فاز ۴ | ⏳ طراحی نشده |
| 2 | `RateLimiter` → interface-based | فاز ۴ | ⏳ طراحی نشده |
| 3 | Recorder واقعی برای candle history (Parquet پیشنهادی) | فاز ۴ | ⏳ طراحی نشده |
| 4 | `fetch_klines` واقعی در NobitexProvider + `CAP_KLINES` | فاز ۴ | ⏳ پیاده‌سازی نشده |
| 5 | min interval poller برای candle 1m (5s پیشنهادی) | فاز ۴ | ⏳ طراحی نشده |
| 6 | `<ramz-chart>` با overlay layer برای اندیکاتورهای آینده | فاز ۴ | ⏳ طراحی نشده |
| 7 | WebSocket صرافی برای real-time price | فاز ۵+ | ⏳ طراحی نشده |
| 8 | `BaseOrderExecutor` برای paper trading آینده | فاز ۵+ | ⏳ طراحی نشده |
| 9 | MasterKeyManager ارتقا (env fallback + rotation + pre-flight) | فاز ۵ / Gen 3b | ⏳ طراحی نشده |
| 10 | `crypto_order` / `crypto_trade` tables (migration v12) | فاز ۵ | ⏳ طراحی نشده |
| 11 | Provider manifest route برای client-side fetch | آینده (بعد از soft launch) | ⏳ طراحی نشده |
| 12 | `symbol_map` و `supported_quotes` گسترش‌پذیر (بدون hardcode سه ارز) | فاز ۳/۴ | 🔍 نیاز به بررسی |
| 13 | `fx` provider عمومی برای چند-فیات | آینده | ⏳ طراحی نشده |
| 14 | `display_currency` به‌صورت string عمومی (نه enum) | فاز ۳/۴ | 🔍 نیاز به بررسی |

---

# بخش چهارم — موارد باز (Open Items)

مواردی که هنوز تصمیم قطعی ندارند و در زمان مشخص بازبینی می‌شوند:

| # | موضوع | تصمیم‌گیرنده | زمان بازبینی |
|---|---|---|---|
| 1 | انتخاب نهایی backend تاریخچه (Parquet vs. جایگزین) | تیم فنی | شروع فاز ۴ |
| 2 | retention policy برای candle history | تیم فنی | شروع فاز ۴ |
| 3 | lightweight-charts یا چارت سفارشی | تیم فنی (بر اساس ارزیابی قابلیت دستکاری) | شروع TASK 80.3 |
| 4 | لیست اندیکاتورهای کلاسیک فاز ۶ | تیم محصول | شروع فاز ۶ |
| 5 | رویکرد client-side fetch (بعد از soft launch) | تیم فنی + محصول | بعد از soft launch |
| 6 | سناریوی paper trading (mark price vs. order book simulation) | تیم محصول | قبل از فاز شبیه‌سازی |
| 7 | جفت‌های crypto/crypto در canonical | تیم فنی | در صورت نیاز فاز ۴+ |
| 8 | سیاست MasterKey در production (env / KMS / Vault) | تیم فنی + امنیت | قبل از فاز ۵ live |

---

## جمع‌بندی

این سند **قرارداد فنی** بین تحلیل فعلی و طراحی فازهای آینده است. اصول کلیدی:

1. **الان ساده‌ترین پیاده‌سازی، با interfaceهای قابل تعویض** — نه over-engineering، نه hardcode.
2. **تصمیمات فاز ۵+ (ترید، شبیه‌سازی) الان گرفته نمی‌شوند**، ولی اثراتشان روی schema و interfaceهای فاز ۳/۴ لحاظ می‌شود.
3. **گسترش‌پذیری ارزها (fiats و جفت‌ها)** از الان در مدل داده لحاظ می‌شود.
4. **چک‌لیست بخش سوم** در شروع هر فاز مرور شود.

**آماده برای دریافت سورس Ramz** و شروع TASK 79.5.