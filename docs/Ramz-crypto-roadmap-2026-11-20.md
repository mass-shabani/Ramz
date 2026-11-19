# Ramz — سند وضعیت پروژه و نقشه راه

> **نسخهٔ سند:** v1.0 — پايان TASK 79.4
> **تاریخ:** 2026-11-20
> **شاخه:** Phase 3 — crypto_coins (در حال انجام، ۴ از ۹ تسک)
> **شاخه‌های تکمیل‌شده:** Phase 0 (زیرساخت)، Phase 1 (crypto_market)، Phase 2 (crypto_providers)

---

# بخش اول — شرح وضعیت و برنامهٔ باقی‌مانده

## ۱.۱. هدف کلی پروژه

**Ramz** یک اپلیکیشن وب تحلیلی-معاملاتی کریپتوکارنسی است که بر بستر فریم‌ورک ماژولار **Massir** توسعه می‌یابد. هدف نهایی، ساخت یک سامانهٔ یکپارچه است که چهار قابلیت اصلی را در یک تجربهٔ کاربری یکپارچه ارائه دهد:

1. **اطلاعات بازار** — نمایش لیست ارزها، قیمت لحظه‌ای، اسپرد بین صرافی‌ها، و مرجع‌قیمت در چند ارز (USDT/RLS/USD).
2. **تحلیل بازار** — ابزارهای تحلیلی، اندیکاتورها، و نمودارهای تخصصی per-coin.
3. **سرویس ترید** — عملیات خرید/فروش (در فازهای آینده، پس از تکمیل لایهٔ داده و اعتبارسنجی).
4. **مدیریت و نظارت** — supervision و system_settings (فازهای پایانی).

## ۱.۲. رویکرد معماری

پروژه از دو قاعدهٔ تغییرناپذیر تبعیت می‌کند:

- **جدایی Service و Page** — ماژول‌های Service (بدون UI) منطق داده و سرویس‌ها را در اختیار می‌گذارند؛ ماژول‌های Page (مصرف‌کننده) UI خود را از طریق Extension System تزریق می‌کنند. غیرفعال شدن هر Page، بدون خطا آن بخش از UI را حذف می‌کند، در حالی که Serviceها به کار خود ادامه می‌دهند.
- **کاهش هزینهٔ منابع** — سرور فقط زمانی از APIها و WebSocketها استفاده می‌کند که UI فعالی وجود داشته باشد (Presence Mechanism). کارهای پس‌زمینه (مثل تاریخچه‌نگاری) به‌عنوان ماژول‌های مستقل و همیشه-فعال طراحی می‌شوند.

## ۱.۳. وضعیت فعلی (پایان TASK 79.4)

| لایه | وضعیت | توضیح |
| :--- | :--- | :--- |
| **زیرساخت Extension** | ✅ کامل | نقاط تزریق، `KNOWN_POINTS`، `find()` در `ModuleRegistry` |
| **crypto_market** | ✅ کامل | Service بدون UI، ۴ endpoint JSON، schema v11 |
| **crypto_providers** | ✅ کامل | ۳ provider (Nobitex/CoinGecko/FX)، Credentials CRUD کامل |
| **crypto_coins** | 🔄 در جریان (۴ از ۹) | سرویس + repository + coins list + settings |
| **crypto_charts** | ⏳ شروع نشده | فاز ۴ |
| **crypto_trading** | ⏳ شروع نشده | فاز ۵ |
| **crypto_analysis** | ⏳ شروع نشده | فاز ۶ (اختیاری) |
| **supervision** | ⏳ شروع نشده | Gen 3 |
| **system_settings** | ⏳ شروع نشده | Gen 3 |

**داده‌های live در حال حاضر:** ۲۸۱ coin از ۳ provider، با اسپرد محاسبه‌شده برای coinهای مشترک.

## ۱.۴. برنامهٔ باقی‌مانده — نگاه کلان

| اولویت | فاز | هدف | اثر کاربری |
| :--- | :--- | :--- | :--- |
| **بالا** | Phase 3 — crypto_coins | تکمیل UI لیست coin + settings + dashboard widget + sidebar | کاربر coinها را می‌بیند، تنظیمات نمایش را کنترل می‌کند |
| **بالا** | Phase 4 — crypto_charts | صفحهٔ نمودار per-coin + کامپوننت چارت + settings | کاربر کندل‌های OHLCV را می‌بیند |
| **متوسط** | Phase 5 — crypto_trading | endpointهای احراز‌دار (Nobitex private)، ثبت سفارش، تاریخچه | کاربر می‌تواند ترید کند |
| **پایین** | Phase 6 — crypto_analysis | اندیکاتورها، سیگنال‌ها، تحلیل تکنیکال | تحلیل خودکار بازار |
| **پایین** | Gen 3 — supervision | audit log viewer، health monitoring | نظارت ادمین |
| **پایین** | Gen 3 — system_settings | مدیریت ماژول‌ها، backup، restart | کنترل سیستم |

## ۱.۵. آمادگی برای فاز بعدی

با تکمیل TASK 79.9 (پایان فاز ۳)، زیرساخت کامل برای فاز ۴ (crypto_charts) آماده خواهد بود:
- `crypto_market_service.get_klines` (route `POST /crypto/market/api/klines/{symbol}`) از فاز ۱ live است.
- providerهای Nobitex/CoinGecko هر دو CAP_KLINES را در آینده (فاز ۴) اعلام می‌کنند.
- الگوی settings UI (`coins_settings.html` + `<script type="module">`) قابل بازاستفاده در `charts_settings.html` است.

---

# بخش دوم — جدول کامل فازها و تسک‌ها

## ۲.۱. فازهای تکمیل‌شده

### ۲.۱.۱. Phase 0 — زیرساخت Extension (۷ تسک + ۱ Massir)

| # | عنوان | خروجی | وضعیت |
| :--- | :--- | :--- | :--- |
| 76.1 | افزودن ۲ نقطهٔ جدید به `KNOWN_POINTS` | `ui.dashboard.widgets`, `ui.account_setting.sections` | ✅ |
| 76.2 | حذف `coin-watchlist` از رجیستری | `services.py`, `main.js` | ✅ |
| 76.3 | dashboard widget slot | `dashboard-content.html`, `user_panel/routes.py` | ✅ |
| 76.4 | `account_setting.sections` در `prepare_context` | `account_setting/routes.py` | ✅ |
| 76.5 | بلوک Connected Services | `settings.html` | ✅ |
| 76.6 | ارتقای `<ramz-sidebar>` | `sidebar.js` (پشتیبانی group) | ✅ |
| 76.7 | مستندسازی | `docs/extension-system.md` | ✅ |
| **MASSIR-NO-1** | افزودن `find(prefix, predicate, type_filter)` به `ModuleRegistry` | `massir/core/registry.py` | ✅ |

### ۲.۱.۲. Phase 1 — crypto_market (Service، بدون UI) — ۱۳ تسک

| # | عنوان | خروجی |
| :--- | :--- | :--- |
| 76.8 / 77.1 | اسکلت ماژول | `manifest.json`, `module.py`, `__init__.py`s |
| 77.2 | migration v10 → v11 | `migration_v10_to_v11.sql` (۴ جدول crypto) |
| 77.3 | symbol_map_repository | CRUD روی `crypto_symbol_map` |
| 77.4 | `create_db.v11.0.sql` | fresh install معادل v10+migration |
| 77.5 | `market_data/interfaces.py` | `BaseCryptoProvider`, `ProviderCoin`, `Kline`, `Orderbook` |
| 77.6 | `market_data/registry.py` | کشف providerها با `services.find()` |
| 77.7 | `market_data/presence.py` | PresenceRegistry (TTL 90s) |
| 77.8 | `types.py` + `aggregator.py` | `CoinData`, `ProviderPrice`, ادغام چند-منبعی + dispersion |
| 77.9 | `market_data/poller.py` | حلقهٔ شرطی به presence + `refresh_now` |
| 77.10 | `market_service/api.py` + wiring | `CryptoMarketService` + `on_all_modules_started` hook |
| 77.11 | Presence routes | `POST /crypto/presence/heartbeat`, `/leave` |
| 77.12 | Coins route | `POST /crypto/market/api/coins` |
| 77.13 | Klines route | `POST /crypto/market/api/klines/{symbol}` |

**باگ‌فیکس در فاز بعد:**
| 78.6-FIX | اصلاح `crypto_market` — استفاده از `app_db_service` + تکمیل access check | `manifest.json`, `module.py`, `routes.py` |

### ۲.۱.۳. Phase 2 — crypto_providers (Service + Settings UI) — ۱۵ تسک

| # | عنوان | خروجی |
| :--- | :--- | :--- |
| 78.1 | اسکلت + فعال‌سازی `system_encryption` | `manifest.json`, `module.py`, `app_settings.json` |
| 78.2 | `credential_repository` | CRUD روی `crypto_credential` |
| 78.3 | `key_manager` + `services.py` + wiring | `MasterKeyManager`, `CredentialService` |
| 78.3-FIX | اصلاح `manifest.requires` | `crypto_market` → `crypto_symbol_map_repository` |
| 78.4 | Nobitex client foundation | `client.py`, `rate_limiter.py`, `symbols.py` + `httpx` به requirements |
| 78.5 | Nobitex provider | `provider.py` + ثبت در `module.py` |
| 78.6 | CoinGecko provider | `client.py`, `provider.py` + ثبت |
| 78.6-FIX | اصلاح access check در crypto_market | رفع باگ امنیتی `has_access` |
| 78.7 | FX provider (mock + navasan stub) | `sources/base.py`, `mock.py`, `navasan.py`, `provider.py` |
| 78.8 | Settings routes + extension | `routes.py`, `templates/`, extension در account_setting |
| 78.9 | Settings templates | `overview.html`, `nobitex.html` |
| 78.9-FIX | رفع multipart form | `_parse_body` Content-Type aware |
| 78.9-FIX-2 | Test Connection + clear + URL section | `settings.html`, `settings_view`, `save` response |
| 78.9-FEATURE-DELETE | حذف credentials + دیالوگ warning | `routes.py`, `nobitex.html`, `settings.html` |
| 78.9-FIX-3 | masked input (بدون trick `username`) | `nobitex.html` (CSS `-webkit-text-security`) |

**تحویل نهایی فاز ۲:**
- ۳ provider live: `nobitex` (USDT/RLS)، `coingecko` (USD)، `fx` (USD→RLS)
- ۲۸۱ coin قابل مشاهده با اسپرد
- Credentials CRUD کامل (save/test/delete) با رمزنگاری AES-256-GCM
- Settings UI در account_setting
- صفر هشدار Chrome

---

## ۲.۲. Phase 3 — crypto_coins (در حال انجام) — ۹ تسک

| # | عنوان | خروجی | وضعیت |
| :--- | :--- | :--- | :--- |
| 79.1 | اسکلت + CoinsService | `manifest.json`, `module.py`, `services.py` | ✅ |
| 79.2 | `user_preference_repository` | CRUD با namespace + helpers (favorites, display_currency, rows_per_page) | ✅ |
| 79.3 | Routes + coins_list template | `POST /crypto/coins/api/list`, `POST /crypto/coins/partials/list` | ✅ |
| 79.4 | Settings routes + template | `api/settings`, `api/settings/save`, `partials/settings` | ✅ |
| **79.5** | **Favorite toggle endpoint + UI** | `POST /crypto/coins/api/favorite/toggle`, دکمه در coins_list | ⏳ |
| **79.6** | **Dashboard widget** | `top-coins-widget.js` + `POST /crypto/coins/api/summary` | ⏳ |
| **79.7** | **Sidebar + Dashboard extensions** | ثبت ۲ آیتم در `ui.sidebar.items` + widget در `ui.dashboard.widgets` | ⏳ |
| **79.8** | **Presence heartbeat** | JS در `coins_list.html` و `coins_settings.html` | ⏳ |
| **79.9** | **End-to-end + مستندسازی** | `docs/crypto-coins.md` + تست نهایی + بامپ `version: 1.0.0` | ⏳ |

**توضیح تسک‌های باقی‌مانده:**

- **79.5** — کاربر در لیست coin می‌تواند با یک کلیک (ستاره) coin را favorite کند. endpoint `POST /crypto/coins/api/favorite/toggle` با body `{canonical, action: "add"|"remove"}`. favoriteها در `crypto_user_preference` (namespace `coins`, key `favorites`) ذخیره می‌شوند. UI: ستون ستاره در جدول + toggle. authorization: `crypto.coins.favorite`.

- **79.6** — یک widget کوچک برای dashboard `/panel` که top 5-10 coin را نشان می‌دهد. `top-coins-widget.js` یک Web Component بومی است که از `POST /crypto/coins/api/summary` (JSON) داده می‌گیرد. از `<ramz-card>` + `<ramz-table>` موجود استفاده می‌کند.

- **79.7** — ثبت ۲ extension در `ui.sidebar.items` (`Crypto Coins`، `Coin Settings`، group=`Crypto`) و ثبت `top-coins-widget` در `ui.dashboard.widgets`. form_id=`crypto.coins.view` و `crypto.coins.favorite` به ترتیب.

- **79.8** — JS حضور در هر دو partial (coins list + settings). `setInterval(30s)` → `POST /crypto/presence/heartbeat {kinds: ["coins"]}`. `beforeunload` → `sendBeacon /crypto/presence/leave {kinds: ["coins"]}`.

- **79.9** — مستندسازی، بامپ نسخه به `1.0.0`، تست کامل end-to-end از login تا dashboard تا coins list تا settings.

---

## ۲.۳. Phase 4 — crypto_charts (برنامه‌ریزی شده) — ~۱۰ تسک

| # | عنوان (پیشنهادی) | خروجی | تخمین |
| :--- | :--- | :--- | :--- |
| 80.1 | اسکلت + ChartsService | `manifest.json`, `module.py`, `services.py` | S |
| 80.2 | `user_preference_repository` (namespace `charts`) | default interval, chart type, theme | S |
| 80.3 | کامپوننت `<ramz-chart>` | Candlestick, lightweight-charts یا SVG | L |
| 80.4 | Route + Template — `charts_view` | `POST /crypto/charts/partials/view`, `POST /crypto/charts/api/klines/{symbol}` | M |
| 80.5 | Route + Template — `charts_settings` | interval, theme, chart type preferences | M |
| 80.6 | Sidebar extensions | `Crypto Charts`, `Chart Settings` (group `Crypto`) | S |
| 80.7 | Presence heartbeat | interval 30s در هر دو partial | S |
| 80.8 | Integration با `crypto_coins` | کلیک روی coin در لیست → باز شدن چارت | S |
| 80.9 | End-to-end + مستندسازی | `docs/crypto-charts.md` | M |
| 80.10 | بامپ `version: 1.0.0` | نهایی‌سازی فاز ۴ | S |

**تحویل مورد انتظار فاز ۴:**
- صفحهٔ چارت per-coin با intervalهای 5m/15m/1h/4h/1d
- تنظیمات per-user (interval پیش‌فرض، theme)
- اتصال از coins list به chart (کلیک روی symbol)
- providerها CAP_KLINES را اعلام می‌کنند و `fetch_klines` را پیاده می‌کنند (در همان فاز ۴).

---

## ۲.۴. Phase 5 — crypto_trading (آیندهٔ نزدیک)

| # | عنوان | خروجی | تخمین |
| :--- | :--- | :--- | :--- |
| 81.1 | اسکلت + TradingService | `manifest.json`, `module.py`, `services.py` | S |
| 81.2 | Authenticated Nobitex client | endpointهای private (orders, wallet) با HMAC/API-key | L |
| 81.3 | Order repository | `crypto_order`, `crypto_trade` tables + migration v11→v12 | M |
| 81.4 | Place order endpoint | `POST /crypto/trading/api/order` + validate + lock | L |
| 81.5 | Cancel / list orders | `POST /crypto/trading/api/orders`, `/cancel` | M |
| 81.6 | Trade UI (sidebar + partial) | فرم خرید/فروش + لیست سفارش‌های باز | L |
| 81.7 | Test Connection واقعی | جایگزینی stub فعلی در crypto_providers | S |
| 81.8 | Audit + supervision hook | activity log + rate limiting | M |
| 81.9 | End-to-end + docs | `docs/crypto-trading.md` | M |

**پیش‌نیازها:** تکمیل فاز ۴ (که providerها `fetch_klines` را پیاده کرده‌اند) + تصمیم دربارهٔ sandbox/live mode.

**نکتهٔ ایمنی:** پیش از هر عملیات واقعی، audit trail کامل و rate limiting الزامی است. حداقل ۲ provider (Nobitex + یکی دیگر) برای test mode.

---

## ۲.۵. Phase 6 — crypto_analysis (اختیاری)

| # | عنوان | خروجی |
| :--- | :--- | :--- |
| 82.1 | اسکلت + AnalysisService | `manifest.json`, `module.py` |
| 82.2 | اندیکاتورهای پایه | SMA/EMA/RSI/MACD روی `get_klines` |
| 82.3 | Hook سفارشی `ON_ANALYSIS_READY` | اطلاع‌رسانی به مصرف‌کننده‌ها |
| 82.4 | UI در charts (overlay) | اندیکاتور روی چارت |
| 82.5 | UI تحلیل جدا | صفحهٔ تحلیل چند-coin |
| 82.6 | ذخیره سیگنال | `crypto_signal` table |
| 82.7 | Docs | `docs/crypto-analysis.md` |

**پیش‌نیاز:** Phase 4 کامل (klines). تحلیل بدون دادهٔ کندل معنا ندارد.

---

## ۲.۶. Gen 3 — supervision (ماژول آیندهٔ Ramz)

| # | عنوان | خروجی |
| :--- | :--- | :--- |
| 83.1 | اسکلت supervision | admin-only UI |
| 83.2 | Activity log viewer | `user_activity_log` با filter/pagination |
| 83.3 | Health dashboard | وضعیت providerها + poller + DB |
| 83.4 | Crypto-specific audit | `crypto_trading` events اگر Phase 5 لاگ داشته باشد |
| 83.5 | End-to-end + docs | `docs/supervision.md` |

**دسترسی:** admin + manager (با rank filter مطابق الگوی admin_panel).

---

## ۲.۷. Gen 3 — system_settings (ماژول آیندهٔ Ramz)

| # | عنوان | خروجی |
| :--- | :--- | :--- |
| 84.1 | اسکلت system_settings | system-admin role (rank=70) تنها مصرف‌کننده |
| 84.2 | Module management | فعال/غیرفعال کردن ماژول‌ها (با warning) |
| 84.3 | Backup / restore DB | SQLite file copy + validation |
| 84.4 | Key rotation | بازتولید master key (با re-encrypt همهٔ credentials) |
| 84.5 | Log viewer | tail live + filter |
| 84.6 | Restart | graceful restart از UI |
| 84.7 | Docs | `docs/system-settings.md` |

**نکتهٔ حساس:** این ماژول به `role='system-admin'` (rank 70، بدون grant فعلی در seed v10) تعلق دارد. تنها کاربری با نقش `super-admin` (rank 80) می‌تواند به system-admin ارتقا دهد.

---

## ۲.۸. جدول خلاصهٔ فازها

| فاز | شماره تسک | تعداد | وضعیت | تحویل کلیدی |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | 76.1–76.7 + MASSIR-NO-1 | ۸ | ✅ کامل | Extension System |
| **Phase 1** | 76.8, 77.1–77.13 + 78.6-FIX | ۱۵ | ✅ کامل | crypto_market Service |
| **Phase 2** | 78.1–78.9 + ۵ fix + ۱ feature | ۱۶ | ✅ کامل | ۳ provider + Credentials CRUD |
| **Phase 3** | 79.1–79.9 | ۹ | 🔄 ۴ از ۹ | coin list UI + settings |
| **Phase 4** | 80.1–80.10 | ~۱۰ | ⏳ | charts UI + klines implementation |
| **Phase 5** | 81.1–81.9 | ~۹ | ⏳ | Trading (authenticated) |
| **Phase 6** | 82.1–82.7 | ~۷ | ⏳ (اختیاری) | Analysis / indicators |
| **Gen 3a** | 83.1–83.5 | ~۵ | ⏳ | supervision |
| **Gen 3b** | 84.1–84.7 | ~۷ | ⏳ | system_settings |
| **جمع** | — | **~۸۶** | **۴۷ انجام‌شده (۵۵٪)** | — |

---

## ۲.۹. قدم بلافاصله بعدی

**TASK 79.5** — Favorite toggle endpoint + UI.

- endpoint: `POST /crypto/coins/api/favorite/toggle`
- body: `{canonical, action: "add"|"remove"}`
- UI: ستون ستاره در `<ramz-table>` coins list
- grant: `crypto.coins.favorite`

پس از آن، 4 تسک باقی‌مانده (79.6–79.9) تا فاز ۳ کامل شود.

---

**آخرین آپدیت:** پایان TASK 79.4 — فاز ۳ (crypto_coins) در میانهٔ راه.
**مرجع همراه:** `task-prompt.v2.0.md` (قوانین کار)، سورس Ramz + massir.