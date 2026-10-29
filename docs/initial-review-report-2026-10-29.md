# گزارش جامع وضعیت پروژه Ramz

## ۱. مشخصات کلی

| مورد | مقدار |
|---|---|
| **نام** | Ramz |
| **نوع** | اپلیکیشن وب تحلیل داده‌های کریپتوکارنسی |
| **Framework** | Massir (ماژولار، پلاگین‌محور) |
| **Python** | 3.13 |
| **DB** | SQLite (schema v7.0، آماده PostgreSQL/MySQL) |
| **Template** | Jinja2 |
| **Frontend** | Native Web Components (بدون فریم‌ورک) |
| **پورت** | 8080 |
| **تم** | Nebula (Dark Glassmorphism) |

---

## ۲. تاریخچه تحول

| مرحله | تغییرات اصلی |
|---|---|
| **نسخه اولیه** | قالب ساده + Lit Components |
| **انتقال به Nebula** | بازطراحی همهٔ صفحات |
| **حذف Lit** | انتقال به `HTMLElement` بومی |
| **بازسازی db_manager** | repositories + workflows + services |
| **user_profile** | صفحهٔ پروفایل مستقل |
| **account_setting** | صفحهٔ تنظیمات با AJAX partials |
| **Session Management** | revoke + auto-eject |
| **Banking** | چند-حساب و چند-کارت |
| **Admin Panel (T48)** | اسکلت admin_panel |
| **Extension System (T49–T53)** | `ComponentExtensionRegistry` + `prepare_context` + `ui_hooks` |
| **Users List (T66)** | جدول کاربران با search + pagination |
| **Users Actions (T67)** | تغییر role، toggle، reset password (با passwordConfirm) |
| **Forms CRUD (T69)** | create/edit/delete forms با passwordConfirm |
| **Access Grants CRUD (T70)** | flat view + filters + mini-matrix |
| **Roles View (T71)** | read-only roles با grants_count |
| **DB v7.0 (T72)** | حذف `condition_of`، افزودن `form_access.level` |
| **T72.1/T72.2 (bugfix)** | رفع ابهامات condition در routes |

---

## ۳. معماری کلی

```
Browser (Web Components)
   ↓ HTTP / AJAX
Massir Framework (FastAPI router, hooks, run groups)
   ↓
Application Modules:
  - auth, home, user_panel, user_profile, account_setting, admin_panel
  - ui_components (تولید + تزریق)
  - template_service, message_view, route_manager, server_manager
  - db_manager
   ↓
system_database → SQLite
```

**اصول طراحی:**
1. ماژولار Massir — هر ماژول مستقل، همه چیز از `context.services`
2. Service-Based — بدون import مستقیم بین ماژول‌ها
3. بدون Lit، بدون Shadow DOM، بدون framework
4. Extension System — تزریق سراسری در کامپوننت‌ها

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
│   │   ├── db_manager_service.py
│   │   ├── models/  (user, profile, access, activity, signup, session_user)
│   │   ├── repositories/  (18 files — condition_repository.py حذف شد)
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
│   │           └── table.js      # ★ از T63
│   │
│   ├── user_panel/              # /panel + dashboard
│   ├── user_profile/            # /profile
│   ├── account_setting/         # /settings/account
│   │
│   └── admin_panel/             # ★ /settings/admin (T48–T71)
│       ├── module.py, routes.py, services.py, manifest.json
│       └── templates/
│           ├── admin_layout.html   # shell + JS
│           └── partials/
│               ├── overview.html
│               ├── users.html       # T66
│               ├── forms.html       # T69
│               ├── access.html      # T70
│               ├── roles.html       # T71
│               └── coming-soon.html
│
├── data/                        # DB + migration backups
│   └── rmz_data.db
│
└── db_scripts/
    ├── create_db.v6.0.sql       # قدیمی
    ├── create_db.v7.0.sql       # ★ فعلی (بدون condition_of، با level)
    ├── migration_v7_remove_condition.sql
    ├── seed_admin_panel.v1.0.sql  # قدیمی
    ├── seed_admin_panel.v2.0.sql  # ★ فعلی (level-based)
    ├── seed_user_panel.v1.0.sql   # قدیمی
    └── seed_user_panel.v2.0.sql   # ★ فعلی
```

---

## ۵. ماژول‌های ثبت‌شده

| ماژول | سرویس | نقش |
|---|---|---|
| `system_logger` | `core_logger` | لاگ |
| `network_fastapi` | `http_api` | FastAPI |
| `system_database` | `database_service` | اتصال DB |
| `template_service` | `template_service`, `menu_manager`, `asset_service` | قالب |
| `db_manager` | `app_db_service` | Facade داده |
| `message_view` | `message_service` | error pages |
| `route_manager` | — | routing |
| `ui_components` | `component_service`, `ui_hooks` | ★ کامپوننت + extension |
| `user_panel` | `panel_service` | پنل |
| `user_profile` | `user_profile_service` | پروفایل |
| `account_setting` | `account_setting_service` | تنظیمات |
| `admin_panel` | `admin_panel_service` | ★ admin |
| `auth` | `auth_service` | ورود/ثبت‌نام |
| `home` | — | landing |
| `server_manager` | — | Uvicorn |

---

## ۶. سیستم Access Control — نسخهٔ level-based (v7.0)

### ۶.۱. مدل داده

**جداول:**
- `role` — ۷ نقش: `super-admin, admin, manager, up-user, user, limit-user, guest`
- `form` — نقاط دسترسی (form_id: `admin_panel.view`, `account.profile.edit`, ...)
- `form_access` — اتصال (role × form) با `level: INTEGER` (`0`=Closed, `≥1`=Open, `>1`=Exceptional)

**❌ `condition_of` حذف شد** (T72)

### ۶.۲. API عمومی

```python
has_access(user_id, form_id, min_level=1, required_condition=None)  # required_condition deprecated
has_public_access(form_id, min_level=1)
get_form_level(user_id, form_id) → int
get_form_level_by_role(role_id, form_id) → int
get_public_level(form_id) → int | None
get_accessible_forms(user_id) → list[str]
invalidate_access_cache(user_id=None)
invalidate_role_cache(role_id=None)
invalidate_form_cache(form_id=None)
```

### ۶.۳. Cache TTLs

| مورد | TTL |
|---|---|
| `is_user_enabled` | ۱۵s |
| `user → role_id` | ۶۰s |
| `role → form → level` | ۶۰s |

### ۶.۴. enforcement در حین تغییر

هر تغییر در `form_access` باعث `invalidate_role_cache(role_id)` و `invalidate_form_cache(form_id)` می‌شود.

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
| `<ramz-coin-watchlist>` | watchlist (روی ramz-table) |
| `<ramz-dialog>` | dialog سراسری |
| **`<ramz-table>`** | ★ جدول data-driven (T63) |

---

## ۸. Extension System (★ جدید — هستهٔ معماری فعلی)

### ۸.۱. نقطه‌های تزریق

**فعال (مصرف‌شده):**
- `ui.user_menu.items` — user-menu.js (link در dropdown)
- `ui.topbar.actions` — topbar.js (button در topbar)

**تعریف‌شده ولی مصرف‌نشده (آینده):**
- `ui.topbar.center`, `ui.topbar.start`, `ui.sidebar.items`, `ui.notifications.items`, `ui.search.items`

### ۸.۲. API

```python
# در start() ماژول:
component_service.register_extension(
    point="ui.user_menu.items",
    data={"label": "Admin Panel", "url": "/settings/admin", "icon": "🛡️", "order": 10},
    form_id="admin_panel.view",
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
window.__ramz.extensions = {"ui.user_menu.items": [...], "ui.topbar.actions": [...]};
```

### ۸.۳. Hooks

- `HOOK_COLLECT` — فایر می‌شود یک بار در `ON_ALL_MODULES_STARTED`
- `HOOK_RESOLVE` — فایر می‌شود per-request در `prepare_context`

ثبت در `context.services` با کلید `ui_hooks`:
```python
{"collect": HOOK_COLLECT, "resolve": HOOK_RESOLVE}
```

---

## ۹. Schema پایگاه داده — v7.0

### ۹.۱. تغییرات v6 → v7

- ❌ حذف `condition_of`
- ✅ `form_access.level: INTEGER NOT NULL DEFAULT 1 CHECK(level >= 0)`
- ✅ Migration: `Closed → 0`, `Others → 1`

### ۹.۲. جداول

| گروه | جداول |
|---|---|
| Lookup | `role`, `form`, `bank`, `subscription`, `activity_type`, `address_type`, `phone_type` |
| Core | `contact`, `people`, `user` |
| Audit | `user_activity_log`, `user_session` |
| Access | `form_access` |
| Contact | `phone`, `post_address`, `email` |
| Banking | `bank_account`, `bank_card` |

### ۹.۳. داده‌های پیش‌فرض

| جدول | داده |
|---|---|
| `role` | ۷ نقش (super-admin, admin, manager, up-user, user, limit-user, guest) |
| `form` | auth, account, admin_panel, user_panel forms |
| `form_access` | همه `level=1` (بدون super-admin) |
| `activity_type`, `address_type`, `phone_type` | استاندارد |

### ۹.۴. Seeds v2.0 (level-based)

- `seed_admin_panel.v2.0.sql` — admin_panel forms + grants (admin, manager فقط، بدون super-admin)
- `seed_user_panel.v2.0.sql` — user_panel.view برای همهٔ نقش‌های احراز-هویت‌شده
- `create_db.v7.0.sql` — شامل seedهای عمومی

**⚠️ seed_admin_panel.v1.0.sql و create_db.v6.0.sql دیگر اجرا نکنند.**

---

## ۱۰. Workflows اصلی

همه بدون تغییر از قبل، جز:
- `has_access(user_id, form_id, min_level=1)` — به جای `required_condition`
- `get_public_level` و `get_public_condition` (deprecated) به جای `get_public_condition` قدیمی

---

## ۱۱. تأیید رمز — passwordConfirm

همان الگوی قبلی (از `ramz-dialog`). لیست اقدامات حساس گسترش یافت:
- Banking operations
- Session revoke
- **admin_panel**: role change, toggle user, reset password, forms CRUD, access grants CRUD

---

## ۱۲. الگوهای توسعه (قواعد ثابت)

| قاعده | توضیح |
|---|---|
| بدون Lit | HTMLElement بومی |
| بدون Shadow DOM | همه CSS در `style.css` |
| بدون import مستقیم بین ماژول‌ها | `context.services.get()` |
| رویدادها: `ramz:*` | namespace |
| تگ‌ها: `ramz-*` | kebab-case |
| `component_service` مالک کامپوننت‌ها | `ui_components` |
| `app_db_service` مالک داده | `db_manager` |
| بدون seed در کد | فقط SQL خارجی |
| همه modal از `ramz-dialog` | بدون `window.confirm` |
| همه errors از `message_service` | error page استاندارد |

---

## ۱۳. الگوهای فرانت‌اند

### ۱۳.۱. AJAX content loading

`content-container` با `ramz:load-content` → fetch POST → inject HTML

### ۱۳.۲. Extension consumption

`window.__ramz.extensions[point]` (از `base.html` تزریق می‌شود)

### ۱۳.۳. Progress bar

`ramz:content-loading` / `ramz:content-loaded` روی `<ramz-progress-bar>`

### ۱۳.۴. Session revoke interceptor

`window.fetch` global — هر 401 با `status: "session_revoked"` → redirect به `/`

### ۱۳.۵. Admin actions pattern

همه action در admin_panel:
1. `appDialog.confirm` — تأیید اولیه
2. `appDialog.passwordConfirm` — تأیید رمز
3. `apiPost(url, body)` — POST JSON
4. بررسی `data.status === 'success'` (نه `resp.ok` — چون سرور همیشه 200 می‌دهد)
5. `showAdminToast` یا `appDialog.alert` بر اساس نتیجه
6. `initXxxPage()` — reload

---

## ۱۴. قواعد Idempotency/Migration

- `create_db.v7.0.sql`: کاملاً idempotent (`IF NOT EXISTS`, `INSERT OR IGNORE`)
- Migration v6→v7: یک‌بارمصرف، با `BEGIN/COMMIT`, `PRAGMA foreign_keys = OFF`
- Seeds: idempotent، ادمین مسئول اجراست

---

## ۱۵. قواعد نام‌گذاری

| مورد | قاعده | مثال |
|---|---|---|
| تگ | `ramz-*` | `ramz-card` |
| فایل JS | kebab-case | `notification-panel.js` |
| کلاس JS | PascalCase با `Ramz` | `RamzCard` |
| Attribute | kebab-case | `user-name` |
| رویداد | `ramz:*` | `ramz:load-content` |
| کلاس CSS | kebab-case | `.card-head-left` |
| فرم ID | dotted | `admin_panel.view` |
| Route | kebab-case | `/settings/admin` |

---

## ۱۶. وضعیت فعلی (پس از T72.2)

### ✅ تکمیل‌شده

- Extension System (`ui.user_menu.items`, `ui.topbar.actions`)
- `ramz-table` به عنوان کامپوننت داده‌محور
- Admin Panel:
  - **Overview** (static)
  - **Users** — list + search + pagination + actions (role, toggle, reset)
  - **Forms** — CRUD با passwordConfirm + grant_count pre-check
  - **Access Grants** — flat view + filter + mini-matrix + create/update/delete (level-based)
  - **Roles** — read-only + View grants shortcut
- Schema v7.0 (level-based، بدون condition_of)
- `user_panel`, `user_profile`, `account_setting` همه به `prepare_context` مهاجرت کرده‌اند
- Access control از `has_access(...min_level=1...)` استفاده می‌کند

### ⚠️ نیازمند attention (پس از حادثه)

- **list_role_form_summary** — باگ LEFT JOIN با `?` (mini-matrix همه ۱ نشان می‌دهد)
- **log message** — `update_grant_condition` در routes.py:1622 (کاسمتیک)

### ⏳ کارهای باقی‌مانده Gen 2

- **T72.3** — bugfix (list_role_form_summary + log message) — **بعد از حادثه با نسخهٔ ایمن**
- **T73** — `role.rank` + enforcement در Users actions
- **T74** — rank filtering در Access Grants و Roles
- **T75** — super-admin فعال + system-admin + per-button form_ids
- **T76** — Polish + Documentation

### ⏳ Gen 3 (بعد از Gen 2)

- **T77** — ماژول `supervision` (activity log, health dashboard, audit trail)
- **T78** — ماژول `system_settings` (برای system-admin)

### ⏳ دیگر (خارج از Gen 2/3)

- 2FA کامل، password reset، email verification، phone verification
- Subscription، billing
- Analytics pages (predictions, markets, portfolio, alerts)
- i18n، notification center

---

## ۱۷. نکات مهم برای توسعه‌دهنده

1. **هرگز Lit اضافه نکن** — معماری به HTMLElement بومی گره خورده
2. **هرگز Shadow DOM اضافه نکن** — همه CSS در `style.css`
3. **هرگز import مستقیم از FastAPI/Massir** — همه از `context.services`
4. **همیشه `_ensure_authenticated` + `has_access` در ابتدای route**
5. **همه action حساس → `appDialog.passwordConfirm`**
6. **همه seed در `db_scripts/*.sql`** — نه در کد
7. **همه migration یک‌بارمصرف** — backup قبل از اجرا
8. **برای افزودن extension: `component_service.register_extension(...)`** — نه import مستقیم
9. **برای resolve: `prepare_context(points=[...])`** — قبل از render
10. **`condition_of` دیگر وجود ندارد** — `form_access.level` استفاده کن (`0`=Closed، `≥1`=Open)
11. **`has_access(user_id, form_id, min_level=1)`** — `required_condition` deprecated
12. **پس از هر تغییر در `form_access` یا `role` → `invalidate_*_cache`**

---

## ۱۸. جمع‌بندی

- **معماری:** ماژولار + Extension-based
- **Access:** level-based، قابل گسترش با rank (pending T73)
- **Admin Panel:** کامل برای CRUD Users/Forms/Access/Roles
- **ریسک نگهداری:** پایین (مستند، یکدست)
- **آمادهٔ Gen 2 پایان:** پس از T72.3، T73–T76

**آخرین آپدیت:** پس از حادثه T72.3 | بازگشت به وضعیت T72.2