# گزارش جامع وضعیت پروژه Ramz

> **نسخهٔ سند:** v3.0 | **Schema:** v11.0 | **وضعیت:** Gen 2 (Admin Panel) کامل + فاز ۰–۲ کریپتو کامل، فاز ۳ در جریان
>
> این سند مرجع اصلی وضعیت فعلی پروژه است. همراه با `task-prompt.v2.0.md` به
> توسعه‌دهنده (انسانی یا AI) داده می‌شود. هدف: درک سریع و دقیق معماری، اجزا،
> الگوها، و مرزهای مجاز.

---

## ۱. مشخصات کلی

| مورد | مقدار |
|---|---|
| **نام** | Ramz |
| **نوع** | اپلیکیشن وب تحلیل داده‌های کریپتوکارنسی |
| **Framework** | Massir 0.2.0 Alpha (ماژولار، پلاگین‌محور) |
| **Python** | 3.13 |
| **DB** | SQLite (schema v11.0، آمادهٔ PostgreSQL/MySQL) |
| **Template** | Jinja2 (async) |
| **Frontend** | Native Web Components (بدون فریم‌ورک) |
| **پورت پیش‌فرض** | 8080 |
| **تم** | Nebula (Dark Glassmorphism) |
| **Gen 2** | ✅ کامل (Admin Panel با per-button + rank + lock) |
| **فاز ۰ (Extension infra)** | ✅ کامل |
| **فاز ۱ (crypto_market)** | ✅ کامل (۱۳ از ۱۳ تسک) |
| **فاز ۲ (crypto_providers)** | ✅ کامل (۳ provider: Nobitex, CoinGecko, FX) |
| **فاز ۳ (crypto_coins)** | 🔄 در جریان (۴ از ۹ تسک — TASK 79.4) |
| **فاز ۴ (crypto_charts)** | ⏳ شروع نشده |
| **Gen 3 (supervision + system_settings)** | ⏳ شروع نشده |

---

## ۲. تاریخچهٔ تحول

### ۲.۱. فازهای اولیه (پیش از کریپتو)

| مرحله | تغییرات اصلی |
|---|---|
| **نسخهٔ اولیه** | قالب ساده + Lit Components |
| **انتقال به Nebula** | بازطراحی همهٔ صفحات |
| **حذف Lit** | انتقال به `HTMLElement` بومی (Light DOM) |
| **بازسازی db_manager** | ۱۳ فاز: repositories + workflows + services |
| **user_profile, account_setting, Session Management, Banking** | ساخت صفحات کاربری |
| **Admin Panel (T48–T75.10)** | Gen 2 کامل: rank + lock + per-button |

### ۲.۲. فاز کریپتو (T76.x به بعد)

| مرحله | تغییرات اصلی |
|---|---|
| **MASSIR-NO-1** | افزودن `ModuleRegistry.find(prefix, predicate, type_filter)` به massir/core/registry.py |
| **TASK 76.1–76.7 (فاز ۰)** | افزودن `ui.dashboard.widgets` و `ui.account_setting.sections` به `KNOWN_POINTS`؛ ارتقای `<ramz-sidebar>` برای مصرف `ui.sidebar.items` با پشتیبانی group؛ حذف `coin-watchlist` از رجیستری؛ بلوک رندر extension در `dashboard-content.html` و `settings.html`؛ به‌روزرسانی `docs/extension-system.md` |
| **TASK 76.8, 77.2–77.13 (فاز ۱)** | ماژول `crypto_market` کامل؛ schema v11 (migration + create_db.v11.0.sql)؛ provider interface، registry، presence، aggregator، poller؛ service API؛ ۴ endpoint JSON (presence × ۲، coins، klines) |
| **TASK 78.1–78.9-FIX-3 (فاز ۲)** | ماژول `crypto_providers` کامل؛ ۳ provider (Nobitex, CoinGecko, FX)؛ Credentials service (AES-256-GCM)؛ Settings UI در account_setting؛ CRUD کامل (overview, save, test, delete)؛ حذف هشدار Chrome |
| **TASK 79.1–79.4 (فاز ۳، در جریان)** | ماژول `crypto_coins` تا نیمهٔ راه: CoinsService، `user_preference_repository`، routes (list/settings)، templates (`coins_list.html`, `coins_settings.html`) |

---

## ۳. معماری کلی

```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Web Components (native HTMLElement, Light DOM)  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                    │ HTTP / AJAX
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Massir Framework 0.2.0 Alpha                           │
│  FastAPI router, hooks, run-order groups                │
│  + ModuleRegistry.find(prefix, predicate, type_filter)  │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Application Modules (19 ماژول فعال)                     │
│  Infrastructure: template, db_manager, ui_components, …│
│  Pages:          home, auth, user_panel, admin_panel, …│
│  Crypto Service: crypto_market, crypto_providers        │
│  Crypto Page:    crypto_coins (در جریان)                │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
system_database + system_encryption → SQLite (v11.0)
```

**اصول طراحی (غیرقابل مذاکره):**

1. **ماژولار Massir** — هر ماژول مستقل، دسترسی فقط از `context.services`
2. **بدون import مستقیم بین ماژول‌ها** — به‌جز دو استثنای رسمی:
   - `provider.py` می‌تواند `app.crypto_market.market_data.interfaces` را import کند (قرارداد عمومی)
   - `services.py` ماژول‌های کریپتو می‌توانند `app.crypto_market.market_data.types` را import کنند (نوع `CoinData`)
3. **بدون Lit، Shadow DOM، یا JS framework**
4. **همهٔ CSS در `style.css` سراسری**
5. **Extension System** — تزریق declarative در کامپوننت‌ها
6. **Fail-closed** برای access checks در endpointهای داده/حساس

---

## ۴. ساختار دایرکتوری (وضعیت فعلی)

```
Ramz/
├── main.py
├── app_settings.json
├── requirements.txt            # + httpx>=0.27.0
│
├── keys/                       # NEW — تولید خودکار
│   └── crypto_credentials.key  # 32-byte AES-256 master key (در .gitignore)
│
├── app/
│   ├── auth/                    # /login, /signup
│   ├── db_manager/              # core data layer + workflows (17 repo)
│   ├── home/                    # landing
│   ├── message_view/            # error pages
│   ├── route_manager/
│   ├── server_manager/
│   ├── template_service/        # base.html, style.css, error.html
│   ├── ui_components/           # ۱۶ کامپوننت (coin-watchlist حذف شد)
│   │   ├── extensions.py        # KNOWN_POINTS: ۹ نقطه (۵ فعال)
│   │   ├── services.py
│   │   ├── module.py
│   │   └── static/js/components/ (۱۶ فایل — بدون coin-watchlist.js)
│   │
│   ├── user_panel/              # /panel + dashboard (از ui.dashboard.widgets)
│   ├── user_profile/            # /profile
│   ├── account_setting/         # /settings/account (از ui.account_setting.sections)
│   ├── admin_panel/             # /settings/admin (Gen 2 کامل)
│   │
│   ├── crypto_market/           # ★ فاز ۱ — Service فقط
│   │   ├── manifest.json        # requires: app_db_service, http_api
│   │   ├── module.py            # wires registry/presence/aggregator/poller/service
│   │   ├── routes.py            # presence + market api endpoints
│   │   ├── market_data/
│   │   │   ├── interfaces.py    # BaseCryptoProvider, CAP_*, ProviderCoin, Kline, Orderbook
│   │   │   ├── registry.py      # ProviderRegistry (uses services.find)
│   │   │   ├── presence.py      # PresenceRegistry (TTL 90s)
│   │   │   ├── aggregator.py    # multi-source merge + FX conversion
│   │   │   ├── poller.py        # conditional loop (presence-aware)
│   │   │   └── types.py         # CoinData, ProviderPrice (consumer-facing DTOs)
│   │   ├── market_service/
│   │   │   └── api.py           # CryptoMarketService (public API)
│   │   └── repositories/
│   │       └── symbol_map_repository.py
│   │
│   ├── crypto_providers/        # ★ فاز ۲ — Service + Account Setting UI
│   │   ├── manifest.json        # requires: crypto_symbol_map_repository + encryption_api + …
│   │   ├── module.py            # wires credentials service + 3 providers
│   │   ├── key_manager.py       # MasterKeyManager (file-based master key)
│   │   ├── services.py          # CredentialService (encrypt/decrypt)
│   │   ├── routes.py            # settings endpoints (overview, save, test, delete)
│   │   ├── repositories/
│   │   │   └── credential_repository.py
│   │   ├── providers/
│   │   │   ├── nobitex/         # client, symbols, rate_limiter, provider
│   │   │   ├── coingecko/       # client, rate_limiter, provider
│   │   │   └── fx/              # base, mock, navasan (stub), provider
│   │   └── templates/partials/
│   │       ├── overview.html
│   │       └── nobitex.html
│   │
│   └── crypto_coins/            # ★ فاز ۳ — در جریان
│       ├── manifest.json        # requires: crypto_market_service + …
│       ├── module.py            # wires service + repo + routes
│       ├── services.py          # CoinsService (passthrough + future)
│       ├── routes.py            # api/list, partials/list, api/settings, api/settings/save, partials/settings
│       ├── repositories/
│       │   └── user_preference_repository.py
│       └── templates/partials/
│           ├── coins_list.html
│           └── coins_settings.html
│
├── data/
│   └── rmz_data.db            # schema v11.0
│
├── docs/                       # ★ extension-system.md به‌روز شد
│   ├── README.md
│   ├── architecture.md
│   ├── access-control.md
│   ├── admin-panel.md
│   └── extension-system.md
│
└── db_scripts/
    ├── create_db.v10.0.sql       # قبل از کریپتو
    ├── create_db.v11.0.sql       # ★ فعلی (شامل جداول crypto + ۶ فرم + ۲۲ گرنت crypto)
    ├── migration_v7_remove_condition.sql
    ├── migration_v8_add_rank.sql
    ├── migration_v9_add_locks.sql
    ├── migration_v10_to_v11.sql  # ★ اجرا شد (کاربر تأیید)
    └── seed_*.sql (v5.0 ادمین، v3.0 user_panel)
```

---

## ۵. ماژول‌های ثبت‌شده (۱۹ ماژول فعال)

### ۵.۱. Massir (System — ۴ ماژول)

| ماژول | سرویس | نقش |
|---|---|---|
| `system_logger` | `core_logger` | لاگ |
| `network_fastapi` | `http_api` | FastAPI |
| `system_database` | `database_service` | اتصال DB |
| **`system_encryption`** | **`encryption_api`** | **AES-256-GCM, RSA-4096, HMAC** (فاز ۲ فعال شد) |

### ۵.۲. Ramz Infrastructure (۶ ماژول)

| ماژول | سرویس | نقش |
|---|---|---|
| `template_service` | `template_service`, `menu_manager`, `asset_service` | قالب + asset |
| `db_manager` | `app_db_service` | Facade داده + Access + Sessions |
| `message_view` | `message_service` | error pages |
| `route_manager` | — | routing |
| `ui_components` | `component_service`, `ui_hooks` | کامپوننت + extension |
| `server_manager` | — | Uvicorn |

### ۵.۳. Ramz Pages (۵ ماژول)

| ماژول | سرویس | نقش |
|---|---|---|
| `user_panel` | `panel_service` | پنل + داشبورد |
| `user_profile` | — | پروفایل مستقل |
| `account_setting` | — | تنظیمات حساب |
| `admin_panel` | `admin_panel_service` | admin panel |
| `auth` | `auth_service` | ورود/ثبت‌نام |
| `home` | — | landing |

### ۵.۴. Crypto (۳ ماژول جدید — تا TASK 79.4)

| ماژول | سرویس | نقش | وضعیت |
|---|---|---|---|
| **`crypto_market`** | `crypto_market_service`, `crypto_symbol_map_repository` | داده بازار (بدون UI) | ✅ فاز ۱ |
| **`crypto_providers`** | `crypto_credentials_service` + ۳ `crypto_provider_*` | Providerها + Credentials + Account Setting UI | ✅ فاز ۲ |
| **`crypto_coins`** | `crypto_coins_service` | صفحهٔ coinها + dashboard widget | 🔄 فاز ۳ (TASK 79.4) |

**نکته:** در فازهای آینده، `crypto_charts` (فاز ۴)، `crypto_analysis` و `crypto_trading` اضافه می‌شوند.

---

## ۶. معماری دامنهٔ کریپتو (جدید)

### ۶.۱. جریان داده

```
Providers (فاز ۲)                    Crypto_market (فاز ۱)              Consumers (فاز ۳+)
─────────────────                    ─────────────────────              ──────────────────
NobitexProvider    ─┐
CoinGeckoProvider  ─┼─▶ registry.by_capability(CAP_COINS)
FxProvider         ─┘              │
                                    ▼
                          asyncio.gather(fetch_coins)
                                    │
                                    ▼
                          [ProviderCoin, ...]
                                    │
                                    ▼
                          aggregator.aggregate()
                                    │
                                    ▼
                          [CoinData, ...]   ← snapshot در poller
                                    │
                                    ▼
                          crypto_market_service
                                    │
                                    ├─▶ /crypto/market/api/coins (JSON)
                                    ├─▶ /crypto/market/api/klines (JSON)
                                    │
                                    ▼
                          crypto_coins_service
                                    │
                                    ├─▶ /crypto/coins/api/list (JSON)
                                    ├─▶ /crypto/coins/api/settings
                                    └─▶ /crypto/coins/partials/* (HTML)
```

### ۶.۲. مدل داده (`CoinData`)

`CoinData` قیمت **همهٔ providerها** را نگه می‌دارد؛ نه یک قیمت aggregate. UI هر provider را در ستون خودش نشان می‌دهد.

```python
@dataclass
class CoinData:
    canonical: str                         # "BTC"
    provider_prices: dict[str, list[ProviderPrice]]  # {"nobitex": [...], "coingecko": [...]}
    reference_prices: dict[str, Decimal]   # median per quote + FX conversion
    price_dispersion_pct: dict[str, Optional[float]]  # (max-min)/median*100 per quote
    available_quotes: list[str]            # ["RLS", "USD", "USDT"]
    sources: list[str]                     # ["coingecko", "nobitex"]
    name: Optional[str]                    # "Bitcoin"
    icon_url: Optional[str]
    updated_at: Optional[datetime]
```

### ۶.۳. Presence & Polling (مدیریت منابع)

Poller با `presence.active_count() > 0` شرطی است. UI heartbeat می‌فرستد (TASK 79.8 برای crypto_coins). اگر هیچ UI فعال نیست، **هیچ API provider صدا زده نمی‌شود** (به‌جز poller که در حالت idle می‌ماند).

### ۶.۴. Provider interface

```python
class BaseCryptoProvider(ABC):
    @property
    def name(self) -> str: ...
    
    @property
    def capabilities(self) -> set[str]:  # {CAP_COINS, CAP_KLINES, CAP_ORDERBOOK}
        ...
    
    @property
    def supported_quotes(self) -> set[str]:  # {"USDT", "RLS"} etc.
        ...
    
    async def fetch_coins(self, symbols=None) -> list[ProviderCoin]: ...
    async def fetch_klines(self, canonical, quote, interval, limit=100) -> list[Kline]: ...
    async def fetch_orderbook(self, canonical, quote, depth=10) -> Optional[Orderbook]: ...  # default: None
```

### ۶.۵. Providers فعلی

| Provider | Quotes | Capabilities | وضعیت |
|---|---|---|---|
| `nobitex` | USDT, RLS | coins | ✅ (fetch_klines stub) |
| `coingecko` | USD | coins | ✅ (per_page=100) |
| `fx` | RLS | coins | ✅ (mock default, navasan stub) |

**FX rate پیش‌فرض (mock):** `1 USD = 900,000 RLS`. قابل override با `crypto_providers.fx.sources.mock.usd_rls`.

---

## ۷. Access Control — سه‌گانه (Gen 2)

بدون تغییر نسبت به سند قبلی: Level + Rank + Lock + per-button. اما **۶ فرم crypto** اضافه شده‌اند:

### ۷.۱. فرم‌های crypto (migration v10→v11)

| form_id | نقش | کاربران با گرنت |
|---|---|---|
| `crypto.coins.view` | مشاهده لیست coinها | user, up-user, manager, admin, super-admin |
| `crypto.coins.favorite` | مدیریت favorites + settings | up-user, manager, admin, super-admin |
| `crypto.charts.view` | مشاهده charts | user, up-user, manager, admin, super-admin |
| `crypto.charts.settings` | تنظیمات charts | up-user, manager, admin, super-admin |
| `crypto.credentials.manage` | مدیریت API keys | up-user, manager, admin, super-admin |
| `crypto.trade.execute` | عملیات ترید (رزرو) | — (هیچ‌کس) |

### ۷.۲. الگوی دسترسی در routes کریپتو

```python
# 1. session + enabled + revoked
session_id, user_id = await _ensure_authenticated(request, db_service, logger)

# 2. grant check (fail-closed)
allowed = await db_service.has_access(user_id, "crypto.coins.view")
if not allowed:
    return 403

# 3. optional: per-button (مثلاً crypto.coins.favorite برای settings)
```

**مهم:** در TASK 78.6-FIX، `crypto_market` از `database_service` به `app_db_service` منتقل شد (چون `DatabaseService` متد `has_access` ندارد). این اصلاح برای همهٔ ماژول‌های کریپتو معیار است.

---

## ۸. Extension System (به‌روز شده)

### ۸.۱. نقاط تزریق (۹ نقطه، ۵ فعال)

| نقطه | مصرف‌کننده | وضعیت |
|---|---|---|
| `ui.user_menu.items` | `<ramz-user-menu>` | ✅ فعال |
| `ui.topbar.actions` | `<ramz-topbar>` | ✅ فعال |
| **`ui.sidebar.items`** | **`<ramz-sidebar>`** | **✅ فعال (فاز ۰)** |
| **`ui.dashboard.widgets`** | **`dashboard-content.html`** | **✅ فعال (فاز ۰)** |
| **`ui.account_setting.sections`** | **`settings.html`** | **✅ فعال (فاز ۰)** |
| `ui.topbar.center` | `<ramz-topbar>` | ⏳ رزرو |
| `ui.topbar.start` | `<ramz-topbar>` | ⏳ رزرو |
| `ui.notifications.items` | `<ramz-notifications>` | ⏳ رزرو |
| `ui.search.items` | `<ramz-search>` | ⏳ رزرو |

### ۸.۲. payload هر نقطهٔ فعال (جدید)

**`ui.sidebar.items`** — append به `<nav class="nav">` (نه جایگزینی):
```python
{
    "label":    "Crypto Coins",
    "endpoint": "/crypto/coins/partials/list",   # یا href
    "icon":     "<svg>...</svg>",
    "order":    100,                              # sort server-side
    "group":    "Crypto",                         # wraps in <ramz-menu-group>
}
```

**`ui.dashboard.widgets`** — server-side render در `dashboard-content.html`:
```python
{
    "html":  "<crypto-top-coins endpoint='/crypto/coins/api/summary'></crypto-top-coins>",
    "order": 10,
}
```

**`ui.account_setting.sections`** — server-side render در `settings.html`:
```python
{
    "id":       "crypto-providers",
    "label":    "Crypto Connections",
    "endpoint": "/settings/crypto/providers/partials/overview",
    "icon":     "<svg>...</svg>",
}
```

### ۸.۳. نکتهٔ URL state در account_setting

`settings_view` در TASK 78.9-FIX-2 اصلاح شد: حالا `prepare_context` را **قبل از** `VALID_SECTIONS` صدا می‌زند و `initial_endpoint` را از `extension_endpoints[sid]` می‌سازد. نتیجه: `?section=crypto-providers` مستقیم overview را بار می‌کند (قبلاً به `personal` fallback می‌کرد).

---

## ۹. Schema پایگاه داده — v11.0

### ۹.۱. تغییرات نسبت به v10

| نسخه | تغییرات |
|---|---|
| v10.0 | seed per-button + `system-admin` |
| **v11.0** | **۴ جدول crypto + ۳ ایندکس + ۶ فرم + ۲۲ گرنت crypto** |

### ۹.۲. جداول جدید v11

```sql
-- Encrypted provider credentials
CREATE TABLE crypto_credential (
    credential_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    provider        TEXT NOT NULL,          -- "nobitex"
    key_type        TEXT NOT NULL,          -- "api_key", "api_secret"
    encrypted_value BLOB NOT NULL,          -- AES-256-GCM ciphertext
    nonce           BLOB NOT NULL,          -- GCM nonce
    tag             BLOB NOT NULL,          -- GCM auth tag
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, provider, key_type),
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

-- Canonical → provider symbol mapping
CREATE TABLE crypto_symbol_map (
    canonical       TEXT NOT NULL,          -- "BTC"
    provider        TEXT NOT NULL,          -- "nobitex"
    provider_symbol TEXT NOT NULL,          -- "btc"
    provider_quote  TEXT,                   -- "USDT" or "" (composite PK)
    PRIMARY KEY (canonical, provider, provider_quote)
);

-- Per-user, per-module preferences (namespace: "coins", "charts")
CREATE TABLE crypto_user_preference (
    user_id INTEGER NOT NULL,
    module  TEXT NOT NULL,
    key     TEXT NOT NULL,                  -- "favorites", "display_currency", ...
    value   TEXT,                           -- JSON for complex types
    PRIMARY KEY (user_id, module, key),
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

-- Price history snapshots (reserved for future recorder)
CREATE TABLE crypto_price_history (
    history_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical   TEXT NOT NULL,
    quote       TEXT NOT NULL,
    price       REAL NOT NULL,
    source      TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### ۹.۳. Seedهای فعلی

- **`create_db.v11.0.sql`** — fresh install (شامل همهٔ داده‌ها + کریپتو)
- **`migration_v10_to_v11.sql`** — اجرا شد (کاربر تأیید کرد)
- `create_db.v10.0.sql` — قبل از کریپتو (نگه داشته شده)
- `migration_v7/v8/v9` — قبلی‌ها
- `seed_admin_panel.v5.0.sql`, `seed_user_panel.v3.0.sql` — idempotent

**⚠️ هرگز seedهای قدیمی (v1–v4 admin، v1–v2 user_panel) روی DB v11 اجرا نکن** — به `form.enabled` یا `condition_id` رفرنس دارند.

---

## ۱۰. فاز ۱ (crypto_market) — نمای کامل

### ۱۰.۱. Endpointها

| Method | Path | Auth | Grant | Purpose |
|---|---|---|---|---|
| POST | `/crypto/presence/heartbeat` | ✅ | — | UI presence |
| POST | `/crypto/presence/leave` | ✅ | — | UI leave |
| POST | `/crypto/market/api/coins` | ✅ | `crypto.coins.view` | snapshot JSON |
| POST | `/crypto/market/api/klines/{symbol}` | ✅ | `crypto.charts.view` | OHLCV JSON |

### ۱۰.۲. Fetched data flow (پس از فاز ۲)

`poll_cycle` با ۳ provider → `564 rows → 281 coins` (تأیید در تست‌ها).

### ۱۰.۳. Background Poller

- `interval=10s`, `fetch_timeout=8s`
- اگر `presence.active_count() == 0` → skip (هیچ provider API صدا زده نمی‌شود)
- `refresh_now(force=False)` debounce 3s (thundering herd protection)

---

## ۱۱. فاز ۲ (crypto_providers) — نمای کامل

### ۱۱.۱. Endpointها (settings)

| Method | Path | Grant | Purpose |
|---|---|---|---|
| POST | `/settings/crypto/providers/partials/overview` | `crypto.credentials.manage` | لیست providerها |
| POST | `/settings/crypto/providers/partials/nobitex` | `crypto.credentials.manage` | فرم Nobitex |
| POST | `/settings/crypto/providers/save` | + password | ذخیرهٔ credentials |
| POST | `/settings/crypto/providers/test` | + password | تست decrypt |
| POST | `/settings/crypto/providers/delete` | + password + extra-warning | حذف credentials |

### ۱۱.۲. CredentialsService API

```python
async def save_credentials(user_id, provider, keys) -> (bool, code)
async def get_credentials(user_id, provider) -> dict | None
async def get_credential(user_id, provider, key_type) -> str | None
async def delete_credentials(user_id, provider) -> bool
async def list_providers(user_id) -> list[str]
async def has_credentials(user_id, provider) -> bool
```

### ۱۱.۳. MasterKeyManager

- File: `{app_dir}/keys/crypto_credentials.key` (32 bytes، `.gitignore`)
- Auto-created در startup اول، `chmod 600` روی Unix
- Warning اگر فایل unsafe permissions داشته باشد
- **Backup ضروری:** از دست دادنش = همهٔ credentials غیرقابل decrypt

### ۱۱.۴. UI flow (account_setting)

```
settings.html sidebar
  └─ "Connected Services" (extension)
       └─ "Crypto Connections" (from crypto_providers)
            └─ content-container → overview.html
                 └─ "Configure/Update" → nobitex.html
                      ├─ Save Credentials (confirm → password → save → reload)
                      ├─ Test Connection (confirm → password → test)
                      └─ Delete Credentials (confirm → confirm-danger → password → delete → reload)
```

**UX polish:**
- پس از Save: فیلدها خالی + `✓ Saved` badge
- پس از Save: `reload_endpoint` → partial رفرش (بدون نیاز به manual)
- هشدار Chrome: رفع با `type="text"` + `-webkit-text-security: disc` (به‌جای `type="password"`)

---

## ۱۲. فاز ۳ (crypto_coins) — وضعیت فعلی

### ۱۲.۱. تکمیل‌شده (TASK 79.1–79.4)

| Component | وضعیت |
|---|---|
| `CoinsService` | ✅ passthrough به `crypto_market_service` |
| `UserPreferenceRepository` | ✅ CRUD با namespace، helpers favorites/currency/rows |
| `/crypto/coins/api/list` | ✅ JSON برای `<ramz-table>` |
| `/crypto/coins/partials/list` | ✅ HTML shell |
| `/crypto/coins/api/settings` | ✅ read preferences |
| `/crypto/coins/api/settings/save` | ✅ save preferences (بدون password) |
| `/crypto/coins/partials/settings` | ✅ HTML + inline `<script type="module">` |
| `coins_list.html` | ✅ `<ramz-card>` + `<ramz-table>` (auto-fetch) |
| `coins_settings.html` | ✅ فرم display_currency + rows_per_page |

### ۱۲.۲. باقی‌مانده (TASK 79.5–79.9)

| # | عنوان |
|---|---|
| 79.5 | Favorite toggle endpoint + JS integration |
| 79.6 | Dashboard widget (`top-coins-widget.js` + `summary` endpoint) |
| 79.7 | Sidebar + Dashboard extensions |
| 79.8 | Presence heartbeat JS در هر دو partial |
| 79.9 | End-to-end + مستندسازی `docs/crypto-coins.md` |

**⚠️ تا TASK 79.7، endpointها live ولی در sidebar user_panel دیده نمی‌شوند** — تست فقط از کنسول مرورگر.

### ۱۲.۳. نکتهٔ فنی `coins_list.html`

`<ramz-table endpoint="/crypto/coins/api/list">` — کامپوننت خودش روی `connectedCallback` fetch می‌کند. **هیچ JS سفارشی برای بارگذاری جدول لازم نیست.** Refresh button فقط `table.reload()` صدا می‌زند.

---

## ۱۳. الگوهای فرانت‌اند (به‌روز شده)

### ۱۳.۱. الگوی section init (anti-dup) — ثابت

```javascript
const state = { initialized: false, currentListener: null };
function initSection() {
    if (state.currentListener) {
        document.removeEventListener('ramz:table-action', state.currentListener);
    }
    state.currentListener = async (e) => { /* handle */ };
    document.addEventListener('ramz:table-action', state.currentListener);
}
```

### ۱۳.۲. `<script type="module">` در partialهای داینامیک (NEW)

`content-container` از `innerHTML = html` استفاده می‌کند. **`<script>` معمولی در innerHTML اجرا نمی‌شود، اما `<script type="module">` بله** (spec HTML5).

**الگوی استفاده:**
```html
<script type="module">
(function () {
    // IIFE برای جلوگیری از نشت global
    // querySelectorها، fetch، event binding
})();
</script>
```

این الگو در `coins_settings.html` استفاده شده. **برای هر partial داینامیک که JS نیاز دارد، از `type="module"` استفاده کنید.**

### ۱۳.۳. `data-require-password` + `data-extra-warning` (NEW در settings.html)

- `data-require-password="true"` → confirm → password → submit
- `data-extra-warning="<message>"` → confirm → **confirm danger** → password → submit (برای عملیات برگشت‌ناپذیر)
- `data-clear-on-success="true"` → clear فیلدها بعد از save
- `reload_endpoint` در response → reload یک partial خاص

**این الگو در `account_setting/templates/settings.html` پیاده شده و برای هر ماژولی که در account_setting section اضافه کند، کار می‌کند.**

### ۱۳.۴. Content-Type aware body parsing (NEW)

`_parse_body` در `crypto_providers/routes.py` و `crypto_coins/routes.py::coins_api_settings_save`:
- `application/json` → `request.json()`
- `multipart/form-data` یا `application/x-www-form-urlencoded` → `request.form()`
- ناشناخته → `{}`

**چرا مهم است:** فرم‌های HTML با `data-ajax` مرورگر به‌صورت `multipart/form-data` ارسال می‌کنند، ولی API clientها JSON. یک endpoint باید هر دو را بپذیرد (باگ در TASK 78.9-FIX کشف شد).

---

## ۱۴. الگوهای backend (به‌روز شده)

### ۱۴.۱. Repository pattern — ثابت

```python
class XRepository:
    TABLE = "x_table"
    def __init__(self, db_service, logger=None): ...
    def _conn(self): return self._db.connection()
    async def get_by_id(...): ...
    # ... CRUD با find_one, find_many, insert, update, delete
```

**باگ مشترک TASK 78.6-FIX:** repositories که `db_service.connection()` صدا می‌زنند، باید `app_db_service` (Ramz facade) بگیرند، نه `database_service` (Massir raw). `DatabaseService` متد `.connection()` ندارد.

### ۱۴.۲. Service facade pattern — ثابت

همهٔ سرویس‌ها در `context.services.set(...)` ثبت می‌شوند. مثال‌های کریپتو:
- `crypto_market_service` → `CryptoMarketService`
- `crypto_symbol_map_repository` → `SymbolMapRepository`
- `crypto_credentials_service` → `CredentialService`
- `crypto_provider_nobitex` / `coingecko` / `fx` → provider instances
- `crypto_coins_service` → `CoinsService`

### ۱۴.۳. Route pattern (سخت‌گیرانه)

```
1. _ensure_authenticated (session + enabled + revoked)
2. per-endpoint grant check (fail-closed)
3. optional: password confirm (mutations)
4. optional: per-button grant check
5. business logic (service)
6. error mapping (HTTP 200 حتی برای error)
7. success response
```

**helperهای مشترک:**
- `_ensure_authenticated` — fail-open (transient DB error → allow، برای جلوگیری از eject دسته‌جمعی)
- `_check_<resource>_view` — fail-closed (DB error → 503، نه allow)
- `_parse_body` — Content-Type aware (JSON یا form)
- `_json_error` — schema ثابت `{status, code, message}`

### ۱۴.۴. Provider registration pattern (NEW)

Providerها در `module.start()` با lazy import ثبت می‌شوند:
```python
try:
    from .providers.nobitex.client import NobitexClient
    from .providers.nobitex.provider import NobitexProvider
    from .providers.nobitex.rate_limiter import RateLimiter
except ImportError as exc:
    logger.log("httpx not installed? ...", level="ERROR")
else:
    rate_limiter = RateLimiter(...)
    client = NobitexClient(...)
    await client.start()
    provider = NobitexProvider(client, logger)
    context.services.set("crypto_provider_nobitex", provider)
```

**دلیل lazy:** اگر `httpx` نصب نباشد، `ImportError` گرفته می‌شود، provider ثبت نمی‌شود، ماژول کرش نمی‌کند.

---

## ۱۵. قواعد Idempotency / Migration (به‌روز شده)

- **`create_db.v11.0.sql`** — idempotent (`IF NOT EXISTS`, `INSERT OR IGNORE`)
- **`migration_v10_to_v11.sql`** — اجرا شد، idempotent
- **`migration_*.sql`** — یک‌بارمصرف، **backup قبل**
- **`seed_*.sql`** — idempotent
- **`keys/crypto_credentials.key`** — در `.gitignore`. **Backup جدا ضروری**

---

## ۱۶. قواعد نام‌گذاری (به‌روز شده)

| مورد | قاعده | مثال |
|---|---|---|
| تگ کریپتو | `crypto_*` | `crypto_coins` |
| فایل JS | kebab-case | `notification-panel.js` |
| کلاس JS | PascalCase با `Ramz` | `RamzTable` |
| Attribute | kebab-case | `user-name`, `data-extra-warning` |
| رویداد | `ramz:*` | `ramz:load-content` |
| کلاس CSS | kebab-case | `.card-head-left` |
| فرم ID (عمومی) | dotted | `admin_panel.users.action.toggle` |
| فرم ID (crypto) | dotted | `crypto.coins.view`, `crypto.credentials.manage` |
| Route (crypto_market) | `/crypto/market/...` | `/crypto/market/api/coins` |
| Route (crypto_coins) | `/crypto/coins/...` | `/crypto/coins/api/list` |
| Route (settings) | `/settings/crypto/...` | `/settings/crypto/providers/partials/nobitex` |
| سرویس | snake_case | `app_db_service`, `crypto_market_service` |
| Provider instance key | `crypto_provider_<name>` | `crypto_provider_nobitex` |

---

## ۱۷. Workflows اصلی (به‌روز شده)

### ۱۷.۱. ورود — ثابت

`POST /login` → `auth_service.login` → session → redirect.

### ۱۷.۲. Eject خودکار — ثابت

هر درخواست محافظت‌شده → `_ensure_authenticated` (fail-open) → اگر نامعتبر: 401 JSON (AJAX) یا redirect (HTML).

### ۱۷.۳. دریافت داده کریپتو (فاز ۳)

```
POST /crypto/coins/api/list
  → _check_coins_view (has_access + fail-closed)
  → if !has_data: coins_service.refresh_now(force=False)  ← debounced 3s
  → coins_service.get_coins()  ← snapshot
  → sort by _sort_key (nobitex USDT desc, ...)
  → _serialize_coin_row per coin (5 columns)
  → 200 {status, currency, total, columns, rows}
```

### ۱۷.۴. ذخیرهٔ credentials (فاز ۲)

```
POST /settings/crypto/providers/save
  → _check_access (crypto.credentials.manage, fail-closed)
  → _parse_body (JSON or form)
  → verify_current_user_password
  → credential_service.save_credentials (encrypt + round-trip verify + store)
  → 200 {status, message, saved_fields, reload_endpoint}
  → Browser: clear fields + reload partial
```

### ۱۷.۵. ذخیرهٔ preferences (فاز ۳)

```
POST /crypto/coins/api/settings/save
  → _check_settings_access (crypto.coins.favorite, fail-closed)
  → Content-Type aware parse
  → validate: display_currency ∈ {USDT, USD, RLS}, rows_per_page ∈ [10, 500]
  → preference_repo.set_display_currency / set_rows_per_page
  → 200 {status, message, saved}
```

---

## ۱۸. وضعیت فعلی و گام‌های بعدی

### ✅ تکمیل‌شده

**Infrastructure (Gen 2):**
- Admin Panel کامل — ۶ بخش، rank/lock/per-button
- Extension System — ۵ نقطهٔ فعال
- `ModuleRegistry.find(prefix, predicate, type_filter)` در Massir

**Crypto Phase 0 (Extension):**
- `ui.sidebar.items`, `ui.dashboard.widgets`, `ui.account_setting.sections` فعال
- `coin-watchlist` حذف شد (فایل روی دیسک، inert)
- `settings_view` extension-aware (`?section=crypto-providers` کار می‌کند)

**Crypto Phase 1 (crypto_market):**
- BaseCryptoProvider، ProviderRegistry، PresenceRegistry، Aggregator، MarketPoller
- ۴ endpoint JSON (presence × ۲، coins، klines)
- schema v11 + migration

**Crypto Phase 2 (crypto_providers):**
- ۳ provider live: Nobitex (535 markets)، CoinGecko (100 coins)، FX (mock USD→RLS)
- Credentials CRUD (AES-256-GCM) — save، test، delete
- Settings UI در account_setting (overview، nobitex form)
- `verify_current_user_password` برای عملیات حساس
- Console clean (بدون هشدار Chrome)

**Crypto Phase 3 (crypto_coins) — تا TASK 79.4:**
- CoinsService + UserPreferenceRepository
- ۵ endpoint: api/list، partials/list، api/settings، api/settings/save، partials/settings
- `coins_list.html` (با `<ramz-table endpoint>` auto-fetch)
- `coins_settings.html` (با inline `<script type="module">`)

### ⏳ در جریان (فاز ۳ باقی‌مانده)

- **TASK 79.5** — Favorite toggle
- **TASK 79.6** — Dashboard widget
- **TASK 79.7** — Sidebar + Dashboard extensions (اولین UI واقعی)
- **TASK 79.8** — Presence heartbeat JS
- **TASK 79.9** — End-to-end + مستندسازی

### ⏳ آینده

- **فاز ۴** — `crypto_charts` (Candlestick + `<ramz-chart>` component + settings)
- **فاز ۵** — WebSocket real-time (اختیاری)
- **`crypto_analysis`** — تحلیل تکنیکال (مصرف‌کننده crypto_charts)
- **`crypto_trading`** — ترید (مصرف‌کننده crypto_market + credentials)
- **Gen 3** — `supervision` (audit) + `system_settings` (system-admin)

---

## ۱۹. نکات مهم برای توسعه‌دهندهٔ بعدی

### قواعد مطلق (بدون استثنا)

1. **بدون Lit، Shadow DOM، JS framework**
2. **بدون import مستقیم بین ماژول‌ها** — به‌جز ۲ استثنا (interfaces، types از crypto_market)
3. **بدون `window.confirm`/`alert`** — `appDialog` (`ramz-dialog`)
4. **بدون seed در Python** — فقط `db_scripts/*.sql`
5. **بدون استفاده از `condition_of`/`form.enabled`/`required_condition`** — حذف شده‌اند
6. **بدون `role_name` برای منطق** — فقط `role_id`
7. **بدون `data-ajax` در partialهای user_panel** — JS settings.html آنجا نیست
8. **برای partial داینامیک با JS:** `<script type="module">` (نه `<script>` عادی)
9. **برای هر helper auth در routes:** کپی از الگو (cross-module import private ممنوع)
10. **fail-open در `_ensure_authenticated`، fail-closed در grant checks**

### قواعد الزامی

11. **همیشه `_ensure_authenticated` + grant check در ابتدای route**
12. **بعد از تغییر `form_access`/`role`/user → `invalidate_*_cache`**
13. **همیشه `data.status === 'success'` چک کن (نه `resp.ok`)**
14. **برای هر table listener: `currentListener` (anti-dup)**
15. **برای افزودن extension: `register_extension(point, data, form_id, module_name)`**
16. **برای resolve: `prepare_context(points=[...])` قبل از render**
17. **Content-Type aware `_parse_body`** برای endpointهایی که هم فرم و هم API client مصرف می‌کند
18. **`db_service` در repositories = `app_db_service`** (نه `database_service`)

### ریسک‌های شناخته‌شده

- **Backup `keys/crypto_credentials.key`** — بدونش همهٔ credentials غیرقابل decrypt
- **Rate limits providerها:** Nobitex 20 req/min، CoinGecko 30 req/min
- **`coin-watchlist.js`** روی دیسک ولی inert — می‌تواند حذف دستی شود
- **CoinGecko `symbol` ممکن است با Nobitex متفاوت باشد** (مثلاً `staked-ether` vs `ETH`) — نیاز به symbol_map آینده

---

## ۲۰. جمع‌بندی

- **معماری:** ماژولار + Extension-based + Fail-closed for data
- **Access Control:** سه‌گانه + per-button + ۶ فرم crypto
- **Admin Panel:** Gen 2 کامل
- **Crypto:** فاز ۰–۲ کامل، فاز ۳ در جریان
- **Schema:** v11.0، idempotent، migration‌پذیر
- **Providers:** ۳ live (Nobitex، CoinGecko، FX) — ~۲۸۱ coin
- **ریسک نگهداری:** پایین — مستند، یکدست، تست‌شده

**آخرین آپدیت:** پس از TASK 79.4
**مرجع همراه:** `task-prompt.v2.0.md` (قوانین کار)، `docs/*.md` (معماری تفصیلی)