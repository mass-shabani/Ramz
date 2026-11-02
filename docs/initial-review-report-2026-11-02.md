# گزارش جامع وضعیت پروژه Ramz

> **نسخهٔ سند:** v2.0 | **Schema:** v10.0 | **وضعیت:** Gen 2 (Admin Panel) کامل
>
> این سند مرجع اصلی وضعیت فعلی پروژه است. همراه با `task-prompt.md` به
> توسعه‌دهنده (انسانی یا AI) داده می‌شود. هدف: درک سریع و دقیق معماری،
> اجزا، الگوها، و مرزهای مجاز.

---

## ۱. مشخصات کلی

| مورد | مقدار |
|---|---|
| **نام** | Ramz |
| **نوع** | اپلیکیشن وب تحلیل داده‌های کریپتوکارنسی |
| **Framework** | Massir 0.2.0 Alpha (ماژولار، پلاگین‌محور) |
| **Python** | 3.13 |
| **DB** | SQLite (schema v10.0، آمادهٔ PostgreSQL/MySQL) |
| **Template** | Jinja2 (async) |
| **Frontend** | Native Web Components (بدون فریم‌ورک) |
| **پورت پیش‌فرض** | 8080 |
| **تم** | Nebula (Dark Glassmorphism) |
| **Gen 2** | ✅ کامل (Admin Panel با per-button + rank + lock) |
| **Gen 3** | ⏳ شروع نشده (supervision + system_settings) |

---

## ۲. تاریخچهٔ تحول

| مرحله | تغییرات اصلی |
|---|---|
| **نسخهٔ اولیه** | قالب ساده + Lit Components |
| **انتقال به Nebula** | بازطراحی همهٔ صفحات |
| **حذف Lit** | انتقال به `HTMLElement` بومی (Light DOM) |
| **بازسازی db_manager** | ۱۳ فاز: repositories + workflows + services |
| **user_profile** | صفحهٔ پروفایل مستقل خارج از پنل |
| **account_setting** | صفحهٔ تنظیمات با AJAX partials |
| **Session Management** | revoke + auto-eject |
| **Banking** | چند-حساب و چند-کارت با enable/disable |
| **Admin Panel (T48)** | اسکلت admin_panel |
| **Extension System (T49–T53)** | `ComponentExtensionRegistry` + `prepare_context` + `ui_hooks` |
| **ramz-table (T63–T65)** | کامپوننت جدول reusable |
| **Users List (T66)** | جدول کاربران با search + pagination |
| **Users Actions (T67)** | تغییر role، toggle، reset password |
| **Forms CRUD (T69)** | create/edit/delete forms |
| **Access Grants CRUD (T70)** | flat view + filters + mini-matrix |
| **Roles View (T71)** | read-only roles با grants_count |
| **Schema v7 (T72)** | حذف `condition_of`، افزودن `form_access.level` |
| **Bugfix batch (T72.1–T72.4)** | رفع باگ‌های condition/level در repo + JS |
| **Schema v8 (T73.1)** | افزودن `role.rank` (hierarchy) |
| **Rank enforcement (T73.2–T73.6)** | Users + Access + Roles filtered by rank |
| **Users view_all (T73.7)** | فرم `admin_panel.users.view_all` |
| **Schema v9 (T74.1)** | حذف `form.enabled`، افزودن `form.lock` + `role.lock` |
| **Lock enforcement (T74.2–T74.4)** | Grants frozen برای form/role قفل |
| **Schema v10 + Per-button (T75.1)** | `create_db.v10.0.sql` + seed v5.0 (14 per-button + system-admin) |
| **Users per-button (T75.2)** | admin/manager: فقط toggle+reset |
| **Forms per-button + lock toggle (T75.3)** | create/edit/delete/lock |
| **Access per-button (T75.4)** | create/edit/delete |
| **Roles CRUD + lock (T75.5.1–T75.5.2)** | کامل (backend + UI) |
| **Access UI merge (T75.7)** | lock merge شده در Actions ستون |
| **Dynamic role list (T75.8)** | assignable_roles از DB |
| **Overview stats (T75.9)** | ۴ کارت آماری + Recent Users |
| **Gen 2 close (T75.10)** | مستندات نهایی + feature matrix |

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
│  Massir Framework                                       │
│  FastAPI router, hooks, run-order groups                │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Application Modules                                    │
│  Service: template, db_manager, ui_components, ...      │
│  Pages:   home, auth, user_panel, admin_panel, ...      │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
system_database → SQLite (v10.0)
```

**اصول طراحی (غیرقابل مذاکره):**

1. **ماژولار Massir** — هر ماژول مستقل، دسترسی به سرویس‌ها فقط از `context.services`
2. **بدون import مستقیم بین ماژول‌ها** — همیشه از سرویس registry
3. **بدون Lit، بدون Shadow DOM، بدون JS framework**
4. **همهٔ CSS در یک فایل سراسری** — `template_service/static/css/style.css`
5. **Extension System** — تزریق declarative در کامپوننت‌های مشترک

---

## ۴. ساختار دایرکتوری (وضعیت فعلی)

```
Ramz/
├── main.py
├── app_settings.json
├── requirements.txt
│
├── app/
│   ├── auth/                    # /login, /signup
│   ├── db_manager/              # core data layer + workflows
│   │   ├── db_manager_service.py    # Facade
│   │   ├── models/  (user, profile, access, activity, signup, session_user)
│   │   ├── repositories/  (17 files — condition_repository.py حذف)
│   │   ├── security/  (password, access, session_utils)
│   │   └── workflows/  (login, signup, profile, settings)
│   │
│   ├── home/                    # landing
│   ├── message_view/            # error pages
│   ├── route_manager/
│   ├── server_manager/
│   ├── template_service/        # base.html, style.css, error.html
│   │
│   ├── ui_components/           # ★ کتابخانه + extension registry
│   │   ├── extensions.py        # ComponentExtensionRegistry + HOOKs
│   │   ├── services.py          # ComponentService + prepare_context
│   │   ├── module.py            # ثبت ui_hooks + fire HOOK_COLLECT
│   │   └── static/js/
│   │       ├── _base.js
│   │       ├── main.js
│   │       └── components/      # 17 کامپوننت
│   │           ├── brand.js, promo.js, card.js, dialog.js
│   │           ├── sidebar.js, topbar.js, menu-group.js, menu-item.js
│   │           ├── collapse-button.js, hamburger-button.js
│   │           ├── search.js, notification-panel.js, user-menu.js
│   │           ├── content-container.js, progress-bar.js
│   │           ├── coin-watchlist.js
│   │           └── table.js
│   │
│   ├── user_panel/              # /panel + dashboard
│   ├── user_profile/            # /profile
│   ├── account_setting/         # /settings/account
│   │
│   └── admin_panel/             # ★ /settings/admin (Gen 2 complete)
│       ├── module.py, routes.py, services.py, manifest.json
│       └── templates/
│           ├── admin_layout.html    # shell + JS (~1300 خط)
│           └── partials/
│               ├── overview.html    # T75.9
│               ├── users.html       # T66, T75.2
│               ├── forms.html       # T69, T74.4, T75.3
│               ├── access.html      # T70, T75.4
│               ├── roles.html       # T71, T75.5.2
│               └── coming-soon.html
│
├── data/
│   └── rmz_data.db
│
├── docs/                        # ★ جدید (T73.8, T75.10)
│   ├── README.md
│   ├── architecture.md
│   ├── access-control.md        # level + rank + lock
│   ├── admin-panel.md           # Gen 2 feature matrix
│   └── extension-system.md
│
└── db_scripts/
    ├── create_db.v6.0.sql       # قدیمی
    ├── create_db.v7.0.sql       # قدیمی
    ├── create_db.v8.0.sql       # قدیمی (با rank)
    ├── create_db.v9.0.sql       # قدیمی (با locks)
    ├── create_db.v10.0.sql      # ★ فعلی (rank + locks + per-button)
    ├── migration_v7_remove_condition.sql
    ├── migration_v8_add_rank.sql
    ├── migration_v9_add_locks.sql
    ├── seed_admin_panel.v1.0.sql  # قدیمی
    ├── seed_admin_panel.v2.0.sql  # قدیمی
    ├── seed_admin_panel.v3.0.sql  # قدیمی (view_all)
    ├── seed_admin_panel.v4.0.sql  # قدیمی
    ├── seed_admin_panel.v5.0.sql  # ★ فعلی (per-button + system-admin)
    ├── seed_user_panel.v1.0.sql   # قدیمی
    ├── seed_user_panel.v2.0.sql   # قدیمی
    └── seed_user_panel.v3.0.sql   # ★ فعلی
```

---

## ۵. ماژول‌های ثبت‌شده

| ماژول | سرویس | نقش |
|---|---|---|
| `system_logger` | `core_logger` | لاگ |
| `network_fastapi` | `http_api` | FastAPI |
| `system_database` | `database_service` | اتصال DB |
| `template_service` | `template_service`, `menu_manager`, `asset_service` | قالب + asset |
| `db_manager` | `app_db_service` | Facade داده + Access + Sessions |
| `message_view` | `message_service` | error pages |
| `route_manager` | — | routing |
| `ui_components` | `component_service`, `ui_hooks` | کامپوننت + extension |
| `user_panel` | `panel_service` | پنل + داشبورد |
| `user_profile` | `user_profile_service` | پروفایل مستقل |
| `account_setting` | `account_setting_service` | تنظیمات حساب |
| `admin_panel` | `admin_panel_service` | admin panel |
| `auth` | `auth_service` | ورود/ثبت‌نام |
| `home` | — | landing |
| `server_manager` | — | Uvicorn |

---

## ۶. Access Control — سه بعد مستقل

Ramz سه محور جدای دسترسی دارد. **همه باید pass شوند** (در جایی که مربوط‌اند):

### ۶.۱. Level (سطح دسترسی هر role×form)

جدول: `form_access (role_id, form_id, level: INTEGER)`

| level | معنا |
|---|---|
| `0` | Closed — no access، صرف‌نظر از `min_level` |
| `≥ 1` | Open — if `level >= min_level` |

API:
```python
has_access(user_id, form_id, min_level=1) -> bool
has_public_access(form_id, min_level=1) -> bool   # guest role
get_form_level(user_id, form_id) -> int           # 0 if no grant
get_form_level_by_role(role_id, form_id) -> int
get_public_level(form_id) -> int | None
get_accessible_forms(user_id) -> list[str]
```

Cache (TTL):
- `is_user_enabled` — 15s
- `user → role_id` — 60s
- `(role_id, form_id) → level` — 60s

Invalidation:
```python
invalidate_access_cache(user_id=None)   # after enabled/role change
invalidate_role_cache(role_id=None)     # after form_access change
invalidate_form_cache(form_id=None)     # after form_access change
```

**`condition_of` حذف شد** — دیگر `required_condition` استفاده نکن.

### ۶.۲. Rank (سلسله‌مراتب نقش)

جدول: `role.rank: INTEGER NOT NULL DEFAULT 0`

| Role | Rank | توضیح |
|---|---|---|
| `super-admin` | 80 | بالاترین — همه‌چیز |
| `system-admin` | 70 | رزرو برای `system_settings` آینده (بدون grant فعلی) |
| `manager` | 60 | مدیر کل سیستم |
| `admin` | 50 | مدیر اجرایی |
| `up-user` | 40 | کاربر با دسترسی بالا |
| `user` | 30 | کاربر معمولی |
| `limit-user` | 20 | کاربر محدود |
| `guest` | 10 | مهمان |

**قاعده:** `current.rank > target.rank` لازم است برای هر عملیات روی کاربر/نقش/گرنت.

اعمال در `AdminPanelService`:
- `set_user_role` — `current > target` و `current > new_role`
- `toggle_user` — `current > target`
- `reset_password` — `current > target`
- `create_grant` / `update_grant_level` / `delete_grant` — `current > role.rank`
- `create_role` — `current > new_rank`
- `update_role` — `current > old_rank` و `current > new_rank`
- `delete_role` — `current > role.rank`

فیلتر در routes:
- `admin_users_list` — بدون `view_all`: `role_rank < current_rank`
- `admin_access_list` — فقط grants roleهای `rank < current_rank`
- `admin_roles_list` — فقط roles با `rank < current_rank`

API:
```python
get_user_rank(user_id) -> int   # 0 if no role
```

### ۶.۳. Lock (قفل گرنت‌ها)

ستون‌ها: `form.lock: INTEGER`، `role.lock: INTEGER`

| Flag | معنا |
|---|---|
| `form.lock = 1` | Grants این form قفل — create/edit/delete ممنوع |
| `role.lock = 1` | Grants این role قفل — create/edit/delete ممنوع |

**قفل ONLY grants را می‌بندد، نه enforcement را:**
- `has_access` هنوز grants را اعمال می‌کند
- فرم/نقش هنوز قابل edit/delete است
- کاربران با آن نقش همچنان فعال

اعمال در:
- `AdminPanelService.create_grant` → `form_locked` / `role_locked`
- `AdminPanelService.update_grant_level` → همان
- `AdminPanelService.delete_grant` → همان

**UI:** lock icon (SVG قفل) در Actions ستون جدول Access (به‌جای دکمه‌ها) + آیکون قفل در ستون Lock جدول Forms/Roles.

### ۶.۴. Role.enabled (برای eject کاربران)

**جدا از lock:** `role.enabled = 0`:
- همهٔ کاربران با آن نقش غیرفعال می‌شوند
- `is_enabled(user_id)` → `False` (JOIN role)
- session بعد از 15s eject
- login رد می‌شود با `account_disabled`

`role.lock = 1` فقط grants را فریز می‌کند، هیچ اثری روی کاربران ندارد.

### ۶.۵. Per-button model (دو لایه)

Admin panel از **دو لایهٔ** مجزا استفاده می‌کند:

**لایه ۱: Section access (6 فرم)**

| form | gate |
|---|---|
| `admin_panel.view` | ورود به admin panel |
| `admin_panel.users.manage` | بخش Users |
| `admin_panel.users.view_all` | دیدن کاربران هم‌rank یا بالاتر |
| `admin_panel.forms.manage` | بخش Forms |
| `admin_panel.access.manage` | بخش Access Grants |
| `admin_panel.roles.view` | بخش Roles |

**لایه ۲: Per-button (14 فرم)**

| form | gate |
|---|---|
| `admin_panel.users.action.change_role` | تغییر role |
| `admin_panel.users.action.toggle` | فعال/غیرفعال |
| `admin_panel.users.action.reset_password` | reset پسورد |
| `admin_panel.forms.action.create` | ساخت فرم |
| `admin_panel.forms.action.edit` | ویرایش فرم |
| `admin_panel.forms.action.delete` | حذف فرم |
| `admin_panel.forms.action.lock` | قفل فرم |
| `admin_panel.access.action.create` | ساخت گرنت |
| `admin_panel.access.action.edit` | ویرایش level گرنت |
| `admin_panel.access.action.delete` | حذف گرنت |
| `admin_panel.roles.action.create` | ساخت نقش |
| `admin_panel.roles.action.edit` | ویرایش نقش |
| `admin_panel.roles.action.delete` | حذف نقش |
| `admin_panel.roles.action.lock` | قفل نقش |

**Default grants (seed v5.0):**

| Role | Section | Per-button |
|---|---|---|
| `super-admin` | همه ۶ | همه ۱۴ |
| `admin` | users, users.view_all, forms, access, roles | users.toggle, users.reset_password |
| `manager` | users, forms, access, roles (بدون view_all) | users.toggle, users.reset_password |
| `system-admin` | — | — (رزرو) |

**نتیجه:**
- **super-admin** — همه‌چیز
- **admin/manager** — فقط view؛ users فقط toggle+reset
- **system-admin** — رزرو برای `system_settings` آینده

---

## ۷. کامپوننت‌های Web (۱۷ کامپوننت)

| کامپوننت | نقش |
|---|---|
| `<ramz-brand>`, `<ramz-promo>`, `<ramz-card>` | پایه |
| `<ramz-topbar>`, `<ramz-sidebar>` | ناوبری |
| `<ramz-menu-group>`, `<ramz-menu-item>` | منو |
| `<ramz-collapse-btn>`, `<ramz-hamburger-btn>` | کنترل |
| `<ramz-search>`, `<ramz-notifications>`, `<ramz-user-menu>` | تعامل |
| `<content-container>` | AJAX loader |
| `<ramz-progress-bar>` | نوار لود |
| `<ramz-coin-watchlist>` | watchlist |
| `<ramz-dialog>` | dialog سراسری |
| **`<ramz-table>`** | جدول data-driven (T63) |

### ۷.۱. ramz-table API

```javascript
table.setColumns(columns)      // [{key, label, type?, className?, align?, width?}]
table.setData(rows)            // array of row objects
table.setLoading(bool)         // toggle .is-loading
table.reload()                 // refetch (if `endpoint` attr set)
table.getRowData(index)        // read raw row

// column type:
"text" | "html" | "avatar" | "badge" | "date" | "number" | "actions"

// action object (in "actions" column):
{
  action:   "change-role",
  icon:     "<svg>...</svg>",
  title:    "tooltip",
  variant:  "" | "danger" | "warning",
  plain:    true | false,       // for non-interactive spans (locked icon)
  data:     {"user-id": "5"},
  href:     "/path",            // renders as <a> instead of <button>
}

// events:
"ramz:table-row-click"  detail: {row, rowIndex}
"ramz:table-action"     detail: {action, row, rowIndex, data}
"ramz:table-loaded"     detail: {url, rowCount}
"ramz:table-error"      detail: {url, status, error}
```

---

## ۸. Extension System

### ۸.۱. نقاط تزریق

**فعال:**
- `ui.user_menu.items` — لینک در dropdown کاربر
- `ui.topbar.actions` — دکمه در topbar

**تعریف‌شده ولی مصرف‌نشده (آینده):**
- `ui.topbar.center`, `ui.topbar.start`, `ui.sidebar.items`
- `ui.notifications.items`, `ui.search.items`

### ۸.۲. API

```python
# در start() ماژول:
component_service.register_extension(
    point="ui.user_menu.items",
    data={"label": "Admin Panel", "url": "/settings/admin",
          "icon": "🛡️", "order": 10,
          "hide_on_path": "/panel"},   # optional
    form_id="admin_panel.view",        # optional (per-user filter)
    module_name="admin_panel",
)

# در route handler قبل از render:
await component_service.prepare_context(
    template_context=context,
    points=["ui.user_menu.items", "ui.topbar.actions"],
    user_id=user_id,
    db_service=db_service,
    app=app,
)
```

`base.html` تزریق می‌کند:
```javascript
window.__ramz.extensions = {
    "ui.user_menu.items": [...],
    "ui.topbar.actions": [...]
};
```

### ۸.۳. Hooks

- `HOOK_COLLECT` — fire یک بار در `ON_ALL_MODULES_STARTED`
- `HOOK_RESOLVE` — fire per-request در `prepare_context`

ثبت در `context.services["ui_hooks"]`:
```python
{"collect": HOOK_COLLECT, "resolve": HOOK_RESOLVE}
```

---

## ۹. Schema پایگاه داده — v10.0

### ۹.۱. تغییرات کلیدی نسبت به v7

| نسخه | تغییرات |
|---|---|
| v7.0 | حذف `condition_of`، `form_access.level` (0=Closed, ≥1=Open) |
| v8.0 | افزودن `role.rank: INTEGER NOT NULL DEFAULT 0` |
| v9.0 | حذف `form.enabled`، افزودن `form.lock`, `role.lock` |
| v10.0 | seed forms گسترش (14 per-button) + `system-admin` role (data-only) |

### ۹.۲. جداول

| گروه | جداول |
|---|---|
| Lookup | `role`, `form`, `bank`, `subscription`, `activity_type`, `address_type`, `phone_type` |
| Core | `contact`, `people`, `user` |
| Audit | `user_activity_log`, `user_session` |
| Access | `form_access` |
| Contact | `phone`, `post_address`, `email` |
| Banking | `bank_account`, `bank_card` |

### ۹.۳. Schema `role`

```sql
CREATE TABLE role (
    role_id     TEXT PRIMARY KEY,
    role_name   TEXT NOT NULL,
    description TEXT,
    rank        INTEGER NOT NULL DEFAULT 0,
    enabled     INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    lock        INTEGER NOT NULL DEFAULT 0 CHECK(lock IN (0, 1)),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### ۹.۴. Schema `form`

```sql
CREATE TABLE form (
    form_id     TEXT PRIMARY KEY,
    form_name   TEXT NOT NULL UNIQUE,
    description TEXT,
    lock        INTEGER NOT NULL DEFAULT 0 CHECK(lock IN (0, 1))
    -- NO enabled column (removed in v9)
);
```

### ۹.۵. Schema `form_access`

```sql
CREATE TABLE form_access (
    role_id TEXT NOT NULL,
    form_id TEXT NOT NULL,
    level   INTEGER NOT NULL DEFAULT 1 CHECK(level >= 0),
    PRIMARY KEY (role_id, form_id),
    FOREIGN KEY (role_id) REFERENCES role(role_id),
    FOREIGN KEY (form_id) REFERENCES form(form_id)
);
```

### ۹.۶. داده‌های پیش‌فرض

| جدول | داده |
|---|---|
| `role` | ۸ نقش: super-admin (80), system-admin (70), manager (60), admin (50), up-user (40), user (30), limit-user (20), guest (10) |
| `form` | ۳۲ فرم: ۱۱ auth/account + 1 user_panel + 20 admin_panel (6 section + 14 per-button) |
| `form_access` | ~۸۳ ردیف گرنت پیش‌فرض |
| `activity_type`, `address_type`, `phone_type` | استاندارد |

### ۹.۷. Seeds فعلی

- `create_db.v10.0.sql` — fresh install (شامل همهٔ داده‌ها)
- `migration_v8_add_rank.sql` — v7→v8 (یک‌بارمصرف)
- `migration_v9_add_locks.sql` — v8→v9 (یک‌بارمصرف)
- `seed_admin_panel.v5.0.sql` — per-button forms + grants (idempotent)
- `seed_user_panel.v3.0.sql` — user_panel.view (idempotent)

**⚠️ هرگز seedهای v1.0/v2.0/v3.0/v4.0 روی DB v10 اجرا نکن** — به `form.enabled` یا `condition_id` رفرنس دارند که حذف شده‌اند.

---

## ۱۰. Admin Panel — نمای کامل

### ۱۰.۱. بخش‌ها (۶)

| Section | URL | Required grant | توضیح |
|---|---|---|---|
| Overview | `?section=overview` | `admin_panel.view` | ۴ کارت آماری + Recent Users |
| Users | `?section=users` | `admin_panel.users.manage` | list + search + pagination + actions |
| Forms | `?section=forms` | `admin_panel.forms.manage` | CRUD + lock toggle + eye icon |
| Access Grants | `?section=access` | `admin_panel.access.manage` | flat view + mini-matrix + CRUD |
| Roles | `?section=roles` | `admin_panel.roles.view` | CRUD + lock + enable toggle |
| Coming Soon | `?section=coming-soon` | — | placeholder |

### ۱۰.۲. Route map

| Method | Path | Purpose | Per-button |
|---|---|---|---|
| GET | `/settings/admin` | shell | — |
| POST | `/settings/admin/partials/{section}` | partial HTML | — |
| POST | `/settings/admin/overview/stats` | stats JSON | — |
| POST | `/settings/admin/users/list` | users JSON | — |
| POST | `/settings/admin/users/set-role` | change role | `users.action.change_role` |
| POST | `/settings/admin/users/toggle` | enable/disable | `users.action.toggle` |
| POST | `/settings/admin/users/reset-password` | reset | `users.action.reset_password` |
| POST | `/settings/admin/forms/list` | forms JSON | — |
| POST | `/settings/admin/forms/create` | create | `forms.action.create` |
| POST | `/settings/admin/forms/update` | edit | `forms.action.edit` |
| POST | `/settings/admin/forms/delete` | delete | `forms.action.delete` |
| POST | `/settings/admin/forms/toggle-lock` | lock | `forms.action.lock` |
| POST | `/settings/admin/access/list` | grants JSON | — |
| POST | `/settings/admin/access/create` | create | `access.action.create` |
| POST | `/settings/admin/access/update` | update level | `access.action.edit` |
| POST | `/settings/admin/access/delete` | delete | `access.action.delete` |
| POST | `/settings/admin/roles/list` | roles JSON | — |
| POST | `/settings/admin/roles/create` | create | `roles.action.create` |
| POST | `/settings/admin/roles/update` | edit | `roles.action.edit` |
| POST | `/settings/admin/roles/delete` | delete | `roles.action.delete` |
| POST | `/settings/admin/roles/toggle-lock` | lock | `roles.action.lock` |

### ۱۰.۳. الگوی همهٔ mutations

```
1. Browser:  appDialog.confirm() → appDialog.passwordConfirm()
2. Browser:  apiPost(url, {fields..., password})
3. Server:   _ensure_authenticated
             → _has_admin_access
             → per-button has_access
             → _verify_admin_password
             → admin_service.method(...)
             → rank + lock checks
             → DB write + cache invalidation
4. Server:   {status, message, ...} با HTTP 200 (حتی برای errors)
5. Browser:  data.status === 'success' ? showAdminToast : appDialog.alert
             → reload section (initXxxPage())
```

### ۱۰.۴. Overview stats endpoint

`POST /settings/admin/overview/stats` response:

```json
{
  "stats": {
    "users": 15, "forms": 32, "grants": 40, "roles": 4
  },
  "recent_users": [
    {"user_id":5, "username":"alice", "full_name":"Alice",
     "initials":"A", "email":"...", "role_name":"user",
     "enabled":true, "created_at":"2026-10-30T..."}
  ]
}
```

- `stats.X = null` اگر viewer دسترسی آن بخش را ندارد
- `grants` فقط برای visible roles (rank < current)
- `roles` فقط rank < current
- `recent_users` با max 5، رعایت `view_all` + rank

### ۱۰.۵. Feature Matrix

| Capability | super-admin | admin | manager |
|---|---|---|---|
| Enter admin panel | ✅ | ✅ | ✅ |
| Overview stats | ✅ all | ✅ scoped | ✅ scoped |
| Users: view | ✅ all | ✅ all (view_all) | ✅ rank<self |
| Users: toggle/reset | ✅ | ✅ | ✅ |
| Users: change role | ✅ | ❌ | ❌ |
| Forms: view | ✅ | ✅ | ✅ |
| Forms: create/edit/delete/lock | ✅ | ❌ | ❌ |
| Access: view | ✅ | ✅ | ✅ |
| Access: create/edit/delete | ✅ | ❌ | ❌ |
| Roles: view | ✅ | ✅ | ✅ |
| Roles: create/edit/delete/lock | ✅ | ❌ | ❌ |

---

## ۱۱. الگوهای فرانت‌اند

### ۱۱.۱. AJAX section loading

```javascript
// هر nav item در admin_layout:
data-endpoint = "/settings/admin/partials/{section}"
data-section  = "{section}"

// click → ramz:load-content event
window.dispatchEvent(new CustomEvent('ramz:load-content', {
  detail: { url: endpoint, section: section }
}));

// content-container listens → fetch → inject HTML
// → fires ramz:content-loaded
// → page JS re-initializes section (initXxxPage)
```

### ۱۱.۲. Section init pattern (anti-duplicate)

```javascript
const xxxState = { initialized: false, cache: [], currentListener: null };

function initXxxPage() {
  // 1. verify DOM elements
  // 2. setColumns
  // 3. bind UI listeners
  // 4. remove previous listener + add new one:
  if (xxxState.currentListener) {
    document.removeEventListener('ramz:table-action', xxxState.currentListener);
  }
  xxxState.currentListener = async (e) => { /* handle */ };
  document.addEventListener('ramz:table-action', xxxState.currentListener);
  // 5. loadData()
}

window.addEventListener('ramz:content-loaded', () => {
  if (getCurrentSection() === 'xxx') initXxxPage();
});

if (getCurrentSection() === 'xxx') setTimeout(initXxxPage, 100);
```

**الگو حیاتی است** — بدون `currentListener`، navigating بین sections باعث duplicate listeners و `Dialog is already open` می‌شود.

### ۱۱.۳. apiPost pattern

```javascript
async function apiPost(url, body) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  let data = {};
  try { data = await resp.json(); } catch (_) {}
  return { ok: resp.ok, status: resp.status, data };
}
```

**مهم:** `resp.ok` بر اساس HTTP status است، نه success. **همیشه `data.status === 'success'` را چک کن**، چون سرور خطاها را هم با HTTP 200 برمی‌گرداند.

### ۱۱.۴. Progress bar

```javascript
window.dispatchEvent(new CustomEvent('ramz:content-loading'));
// ...ajax...
window.dispatchEvent(new CustomEvent('ramz:content-loaded'));
```

`<ramz-progress-bar>` در topbar listens و animates.

### ۱۱.۵. Session revoked interceptor

در `ui_components/main.js`:
```javascript
window.fetch = async function (...args) {
  const resp = await originalFetch.apply(this, args);
  if (resp.status === 401) {
    const clone = resp.clone();
    const data = await clone.json().catch(() => null);
    if (data?.status === 'session_revoked') {
      window.location.href = '/';
    }
  }
  return resp;
};
```

---

## ۱۲. الگوهای backend

### ۱۲.۱. Repository pattern

```python
from ._helpers import db_insert, db_update, db_delete, result_ok, result_last_id

class XRepository:
    TABLE = "x_table"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    async def get_by_id(self, id): ...
    async def list_all(self): ...
    async def create(self, **kwargs): ...
    async def update(self, id, **fields): ...
    async def delete(self, id): ...
```

### ۱۲.۲. Service facade pattern

همهٔ متدها روی `db_manager_service.py` با prefix `admin_*`:
- `admin_list_users`, `admin_count_users`
- `admin_create_form`, `admin_update_form`, `admin_delete_form`, `admin_set_form_lock`
- `admin_create_grant`, `admin_update_grant_level`, `admin_delete_grant`
- `admin_create_role`, `admin_update_role`, `admin_delete_role`, `admin_set_role_lock`

### ۱۲.۳. AdminPanelService pattern

منطق business + validation + rank enforcement:

```python
async def set_user_role(self, target_user_id, new_role_id, current_user_id):
    target = await self.db.get_user_by_id(target_user_id)
    if not target:
        return False, "user_not_found"
    new_role = await self.db._role_repo.get_by_id(new_role_id)
    if not new_role:
        return False, "role_not_found"
    current_rank = await self.db.get_user_rank(current_user_id)
    target_rank = int(target.role_rank or 0)
    new_role_rank = int(new_role.get("rank") or 0)
    if current_rank <= target_rank:
        return False, "insufficient_rank"
    if current_rank <= new_role_rank:
        return False, "insufficient_rank"
    ok, code = await self.db.admin_set_user_role(target_user_id, new_role_id)
    return ok, code
```

### ۱۲.۴. Route pattern

```python
@http_api.post("/settings/admin/xxx/yyy", response_class=http_api.JSONResponse)
async def admin_xxx_yyy(request: http_api.Request):
    # 1. auth
    user_id, redirect = await _ensure_authenticated(request)
    if redirect:
        return http_api.JSONResponse(
            content={"status": "error", "code": "session_expired"},
            status_code=401)

    # 2. admin access
    if not await _has_admin_access(user_id):
        return http_api.JSONResponse(..., status_code=403)

    # 3. section access
    try:
        can_section = await db_service.has_access(user_id, "admin_panel.xxx.manage")
    except Exception:
        can_section = False
    if not can_section:
        return http_api.JSONResponse(..., status_code=403)

    # 4. per-button
    try:
        can_action = await db_service.has_access(user_id, "admin_panel.xxx.action.yyy")
    except Exception:
        can_action = False
    if not can_action:
        return http_api.JSONResponse(
            content={"status": "error", "code": "no_permission",
                     "message": "You do not have permission to ..."},
            status_code=403)

    # 5. parse body
    try: body = await request.json()
    except Exception: body = {}

    # 6. password confirm
    if not await _verify_admin_password(user_id, body.get("password", "")):
        return http_api.JSONResponse(
            content={"status": "error", "code": "invalid_password",
                     "message": "The password you entered is incorrect."},
            status_code=200)

    # 7. service call
    try:
        ok, code = await admin_service.method(...)
    except Exception as exc:
        if logger: logger.log(..., level="ERROR", tag="admin")
        ok, code = False, "internal_error"

    # 8. error mapping
    if not ok:
        messages = {...}
        return http_api.JSONResponse(
            content={"status": "error", "code": code, "message": messages.get(code, ...)},
            status_code=200)

    # 9. success
    return http_api.JSONResponse(
        content={"status": "success", "message": "...", ...},
        status_code=200)
```

---

## ۱۳. قواعد Idempotency / Migration

- **`create_db.v10.0.sql`** — کاملاً idempotent (`IF NOT EXISTS`, `INSERT OR IGNORE`)
- **`migration_*.sql`** — یک‌بارمصرف، با `BEGIN/COMMIT`, `PRAGMA foreign_keys = OFF`؛ **backup قبل**
- **`seed_*.sql`** — idempotent، ادمین مسئول اجرا
- **قبل از هر migration: `cp data/rmz_data.db data/rmz_data.db.bak-YYYYMMDD`**

---

## ۱۴. قواعد نام‌گذاری

| مورد | قاعده | مثال |
|---|---|---|
| تگ | `ramz-*` | `ramz-card` |
| فایل JS | kebab-case | `notification-panel.js` |
| کلاس JS | PascalCase با `Ramz` | `RamzCard` |
| Attribute | kebab-case | `user-name` |
| رویداد | `ramz:*` | `ramz:load-content` |
| کلاس CSS | kebab-case | `.card-head-left` |
| فرم ID | dotted | `admin_panel.users.action.toggle` |
| Route | kebab-case | `/settings/admin` |
| سرویس | snake_case | `app_db_service` |

---

## ۱۵. Workflows اصلی

### ۱۵.۱. ورود

```
POST /login
  → auth_service.login(username, password, request)
    → login_workflow.login_strict
      → user_repository.get_by_username (include_password=True)
      → چک enabled کاربر
      → چک role_enabled (JOIN role)   ← جدید (v9)
      → verify_password (bcrypt)
      → needs_rehash? update_password_hash
      → activity_repository.log("login")
      → session_repository.create()
  → build_session_user → session["user"]
  → redirect به /panel
```

### ۱۵.۲. Eject خودکار

```
هر درخواست محافظت‌شده
  → _ensure_authenticated / _check_session
    → is_user_enabled (TTL 15s، شامل JOIN role.enabled)
    → is_session_valid (TTL 15s)
  → اگر نامعتبر:
     • HTML: redirect به / یا /login
     • AJAX: 401 JSON {status: "session_revoked"}
  → fetch interceptor redirect
```

### ۱۵.۳. تغییر role (admin panel)

```
POST /settings/admin/users/set-role
  → _ensure_authenticated
  → _has_admin_access
  → has_access(users.manage)
  → has_access(users.action.change_role)   ← per-button
  → verify password
  → admin_service.set_user_role(target_id, new_role, current_id)
    → get_user_by_id(target) → role_rank
    → get role(new_role) → new_role_rank
    → current_rank > target_rank
    → current_rank > new_role_rank
    → admin_set_user_role(target_id, new_role)
    → invalidate_access_cache(target_id)
  → {status: "success"}
```

---

## ۱۶. وضعیت فعلی (پس از T75.10)

### ✅ تکمیل‌شده

**Extension & Components:**
- Extension System (`ui.user_menu.items`, `ui.topbar.actions`)
- `ramz-table` به‌عنوان کامپوننت داده‌محور
- ۱۷ کامپوننت Web بومی

**Admin Panel — Gen 2 (کامل):**
- Overview با ۴ کارت آماری + Recent Users
- Users: list + search + pagination + 3 actions (rank + per-button + password confirm)
- Forms: CRUD + lock toggle + eye icon + per-button
- Access Grants: flat view + mini-matrix + level-based CRUD + lock-aware + per-button
- Roles: full CRUD + lock toggle + enable toggle + per-button
- Dynamic role list در change-role (assignable_roles از DB)

**Access Control:**
- Level-based (v7) — `form_access.level`
- Rank-based (v8) — `role.rank` + enforcement
- Lock-based (v9) — `form.lock`, `role.lock`
- Per-button model (v10) — 14 forms action
- Role.enabled ejection (v9)

**Schema:**
- v10.0 idempotent (`create_db.v10.0.sql`)
- 3 migration files (v7→v8, v8→v9)
- seed v5.0 + seed v3.0 user_panel

**Documentation:**
- `docs/README.md`, `docs/architecture.md`
- `docs/access-control.md`, `docs/admin-panel.md`
- `docs/extension-system.md`

**Migrationها:**
- `has_access(user_id, form_id, min_level=1)` — `required_condition` deprecated
- `user_panel`, `user_profile`, `account_setting` همه به `prepare_context` مهاجرت کرده

### ⏳ Gen 3 (بعد از Gen 2)

| ماژول | هدف |
|---|---|
| **`supervision`** | Activity log viewer + system health + audit trail (admin + manager) |
| **`system_settings`** | برای system-admin (rank=70) — مدیریت فایل، manifest، module، backup، restart |

### ⏳ ویژگی‌های دیگر (خارج از Gen 2/3)

- **2FA کامل** — TOTP secret + QR + verify
- **Password reset** — فراموشی رمز با ایمیل
- **Email/Phone verification** — با لینک/SMS
- **Subscription** — تغییر پلن + پرداخت
- **Billing** — مدیریت فاکتورها
- **Delete account** — حذف کامل با تأیید دو مرحله‌ای
- **Analytics pages** — predictions, markets, portfolio, alerts
- **Social login** — Google/GitHub
- **i18n** — چندزبانه
- **Notification center** — سیستم اعلان کامل

---

## ۱۷. نکات مهم برای توسعه‌دهنده بعدی

### قواعد مطلق (بدون استثنا)

1. **هرگز Lit اضافه نکن** — HTMLElement بومی، Light DOM
2. **هرگز Shadow DOM اضافه نکن** — همهٔ CSS در `style.css` سراسری
3. **هرگز import مستقیم بین ماژول‌ها** — همه از `context.services.get()`
4. **هرگز `window.confirm` / `window.alert`** — فقط `appDialog` (`ramz-dialog`)
5. **هرگز seed در کد Python** — فقط `db_scripts/*.sql`
6. **هرگز migration idempotent رو دوباره اجرا نکن** — یک‌بارمصرف، backup قبل
7. **هرگز `condition_of` / `form.enabled` / `required_condition` استفاده نکن** — حذف شده‌اند
8. **هرگز **—** از `role_name` برای منطق** — `role_id` شناسهٔ پایدار است؛ `role_name` فقط display

### قواعد الزامی

9. **همیشه `_ensure_authenticated` + `_has_admin_access` + per-button `has_access` در ابتدای route**
10. **همهٔ mutations نیازمند `passwordConfirm`**
11. **بعد از هر تغییر در `form_access` / `role` / user → `invalidate_*_cache`**
12. **همیشه `data.status === 'success'` چک کن (نه `resp.ok`)**
13. **برای هر table listener: `currentListener` (anti-dup)**
14. **برای هر component stateful: `open`/`close` + `ramz:close-dropdowns`**
15. **برای افزودن extension: `component_service.register_extension(...)` — نه import**
16. **برای resolve: `prepare_context(points=[...])` قبل از render**

### هرگز نکن

- اضافه‌کردن لایهٔ جدید بدون مستندسازی در `docs/`
- تغییر schema بدون migration + backup
- اجرای SQL مستقیم روی `data/rmz_data.db` (به‌جز backup/restore/read-only)
- تغییر `has_access` signature (backward compat حفظ)
- افزودن role بدون rank صریح

---

## ۱۸. جمع‌بندی

- **معماری:** ماژولار + Extension-based
- **Access Control:** سه‌گانه Level + Rank + Lock + Per-button
- **Admin Panel:** Gen 2 کامل — ۶ بخش، همه CRUD، با rank/lock/per-button
- **Schema:** v10.0، idempotent، migration‌پذیر
- **ریسک نگهداری:** پایین (مستند، یکدست، تست‌شده)
- **آمادهٔ Gen 3:** شروع `supervision` module

**آخرین آپدیت:** پس از T75.10 — Gen 2 close
**مرجع همراه:** `task-prompt.md` (قوانین کار)، `docs/*.md` (معماری تفصیلی)