# گزارش جامع وضعیت پروژه Ramz

> **هدف:** این سند مرجع کامل وضعیت فعلی پروژه Ramz است. با خواندن آن، توسعه‌دهنده‌های انسانی و مدل‌های هوش مصنوعی می‌توانند تصویر دقیقی از معماری، اجزا، workflows و قواعد پروژه به دست آورند.

---

## ۱. مشخصات کلی پروژه

| مورد | مقدار |
|---|---|
| **نام پروژه** | Ramz |
| **نوع** | اپلیکیشن وب تحلیل داده‌های کریپتوکارنسی |
| **فریم‌ورک بک‌اند** | Massir (ماژولار، مبتنی بر پایتون) |
| **زبان backend** | Python 3.13 |
| **پایگاه داده** | SQLite (با آمادگی برای PostgreSQL و MySQL) |
| **قالب‌بند بک‌اند** | Jinja2 |
| **فرانت‌اند** | Native Web Components (بدون فریم‌ورک) |
| **پورت پیش‌فرض** | 8080 |
| **قالب طراحی** | Nebula (Dark Glassmorphism) |

---

## ۲. تاریخچه تحول

پروژه Ramz در طول توسعه چند مرحله مهم را پشت سر گذاشته است:

| مرحله | تغییرات اصلی |
|---|---|
| **نسخه اولیه** | قالب ساده با `theme.css` و Lit Components |
| **انتقال به Nebula** | جایگزینی CSS، بازطراحی همه صفحات با Dark Glassmorphism |
| **حذف Lit** | انتقال کامل از Lit به `HTMLElement` بومی |
| **استخراج `ui_components`** | ایجاد ماژول مستقل کتابخانه‌ای با ۱۵+ کامپوننت |
| **بازسازی `db_manager`** | ۱۳ فاز پیوسته: repositories + workflows + services |
| **ساخت `user_profile`** | صفحه پروفایل مستقل خارج از پنل |
| **ساخت `account_setting`** | صفحه تنظیمات با AJAX partials |
| **افزودن Session Management** | جدول `user_session` + revoke + auto-eject |
| **تکمیل Banking** | مدیریت چند-حساب و چند-کارت با enable/disable |
| **استانداردسازی خطا** | `ramz-dialog` + `message_service` برای همه پیام‌ها |

---

## ۳. معماری کلی

### ۳.۱. لایه‌ها

```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Web Components (native HTMLElement)             │  │
│  │  • ramz-sidebar, ramz-card, ramz-dialog, ...     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                    │ HTTP / AJAX
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Massir Framework                                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  FastAPI Router (Route Manager)                  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Application Modules                                    │
│  ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┐   │
│  │ auth │ home │ user │ user │ acct │ ui_  │ ...  │   │
│  │      │      │panel │ prof │ set  │ comp │      │   │
│  └──────┴──────┴──────┴──────┴──────┴──────┴──────┘   │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  db_manager (Facade + Repositories + Workflows)         │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  system_database (Framework Service)                    │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  SQLite / PostgreSQL / MySQL                            │
└─────────────────────────────────────────────────────────┘
```

### ۳.۲. اصل طراحی

1. **ماژولار Massir:** هر ماژول مستقل است و از طریق `ModuleContext` سرویس‌ها را می‌گیرد.
2. **Service-Based:** بین ماژول‌ها فقط از طریق سرویس‌های ثبت‌شده در `context.services` ارتباط برقرار می‌شود.
3. **بدون Lit:** همه کامپوننت‌ها `HTMLElement` بومی هستند.
4. **بدون Shadow DOM:** همه استایل‌ها در `style.css` سراسری.
5. **بدون Bootstrap/JS Frameworks:** فقط Vanilla JS و CSS خالص.

---

## ۴. ساختار دایرکتوری

```
Ramz/
├── main.py                          # نقطه ورود
├── app_settings.json                # تنظیمات مرکزی
├── requirements.txt
│
├── app/
│   ├── auth/                        # ورود / ثبت‌نام / خروج
│   │   ├── manifest.json
│   │   ├── module.py
│   │   ├── services.py
│   │   └── templates/
│   │       ├── login.html
│   │       └── signup.html
│   │
│   ├── db_manager/                  # لایه دسترسی به داده
│   │   ├── manifest.json
│   │   ├── module.py
│   │   ├── db_manager_service.py    # Facade
│   │   ├── security/
│   │   │   ├── password.py          # bcrypt
│   │   │   ├── access.py            # AccessChecker
│   │   │   └── session_utils.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── profile.py
│   │   │   ├── access.py
│   │   │   ├── activity.py
│   │   │   ├── signup.py
│   │   │   └── session_user.py
│   │   ├── repositories/            # ۱۸ repository
│   │   │   ├── _helpers.py
│   │   │   ├── user_repository.py
│   │   │   ├── people_repository.py
│   │   │   ├── contact_repository.py
│   │   │   ├── email_repository.py
│   │   │   ├── phone_repository.py
│   │   │   ├── address_repository.py
│   │   │   ├── role_repository.py
│   │   │   ├── form_repository.py
│   │   │   ├── condition_repository.py
│   │   │   ├── form_access_repository.py
│   │   │   ├── subscription_repository.py
│   │   │   ├── activity_repository.py
│   │   │   ├── session_repository.py
│   │   │   ├── bank_repository.py
│   │   │   ├── bank_account_repository.py
│   │   │   ├── bank_card_repository.py
│   │   │   ├── address_type_repository.py
│   │   │   └── phone_type_repository.py
│   │   └── workflows/
│   │       ├── login_workflow.py
│   │       ├── signup_workflow.py
│   │       ├── profile_workflow.py
│   │       └── settings_workflow.py
│   │
│   ├── home/                        # صفحه لندینگ
│   │   ├── manifest.json
│   │   ├── module.py
│   │   ├── routes.py
│   │   ├── static/
│   │   └── templates/
│   │
│   ├── message_view/                # سرویس پیام‌های خطا
│   │   ├── manifest.json
│   │   ├── module.py
│   │   ├── services.py
│   │   └── templates/message.html
│   │
│   ├── route_manager/               # مدیریت مسیرها
│   ├── server_manager/              # مدیریت Uvicorn
│   │
│   ├── template_service/            # سرویس قالب و asset
│   │   ├── manifest.json
│   │   ├── module.py
│   │   ├── manager.py
│   │   ├── static/
│   │   │   ├── assets/favicon.svg
│   │   │   └── css/style.css        # تم سراسری
│   │   └── templates/
│   │       ├── base.html
│   │       ├── error.html
│   │       └── components/
│   │           ├── navbar.html
│   │           └── footer.html
│   │
│   ├── ui_components/               # کتابخانه کامپوننت‌ها
│   │   ├── manifest.json
│   │   ├── module.py
│   │   ├── services.py              # ComponentService
│   │   └── static/js/
│   │       ├── _base.js
│   │       ├── main.js
│   │       └── components/          # ۱۵+ کامپوننت
│   │           ├── brand.js
│   │           ├── promo.js
│   │           ├── menu-group.js
│   │           ├── menu-item.js
│   │           ├── sidebar.js
│   │           ├── collapse-button.js
│   │           ├── hamburger-button.js
│   │           ├── card.js
│   │           ├── topbar.js
│   │           ├── search.js
│   │           ├── notification-panel.js
│   │           ├── user-menu.js
│   │           ├── content-container.js
│   │           ├── progress-bar.js
│   │           ├── coin-watchlist.js
│   │           └── dialog.js
│   │
│   ├── user_panel/                  # پنل کاربری
│   │   ├── manifest.json
│   │   ├── module.py
│   │   ├── routes.py
│   │   ├── services.py
│   │   └── templates/
│   │       ├── dashboard.html       # shell پنل
│   │       ├── panel_layout.html
│   │       └── partials/
│   │           └── dashboard-content.html
│   │
│   ├── user_profile/                # پروفایل مستقل
│   │   ├── manifest.json
│   │   ├── module.py
│   │   ├── routes.py
│   │   └── templates/profile.html
│   │
│   └── account_setting/             # تنظیمات حساب
│       ├── manifest.json
│       ├── module.py
│       ├── routes.py
│       └── templates/
│           ├── settings.html        # shell
│           └── partials/            # ۸ partial
│               ├── personal.html
│               ├── contact.html
│               ├── password.html
│               ├── twofa.html
│               ├── subscription.html
│               ├── banking.html
│               ├── sessions.html
│               └── danger.html
│
└── data/
    ├── create_db.sql                # schema اصلی (v4.1)
    ├── create_db.v4.0.sql           # نسخه پشتیبان
    ├── create_db.v3.1.sql           # نسخه قدیمی‌تر
    ├── rmz_data.db                  # SQLite
    ├── seed_auth.sql
    ├── seed_user_profile.sql
    ├── seed_account_setting.sql
    └── migration_005_address_phone_fk.sql
```

---

## ۵. ماژول‌های ثبت‌شده

### ۵.۱. ماژول‌های سیستمی

| ماژول | نقش |
|---|---|
| `sys_logger` | ثبت رویدادها با tag و level |
| `system_database` | اتصال چند-دیتابیسی (SQLite/PostgreSQL/MySQL) |
| `network_fastapi` | ارائه‌دهنده FastAPI |
| `template_service` | رجیستری قالب، asset و static files |
| `route_manager` | مدیریت متمرکز مسیرها |
| `server_manager` | راه‌اندازی Uvicorn |

### ۵.۲. ماژول‌های برنامه

| ماژول | سرویس ارائه‌شده | مسئولیت |
|---|---|---|
| `db_manager` | `app_db_service` | دسترسی به داده + Access Control + Sessions |
| `ui_components` | `component_service` | کتابخانه کامپوننت‌ها |
| `message_view` | `message_service` | صفحه خطا / پیام‌های سیستمی |
| `auth` | `auth_service` | ورود، ثبت‌نام، خروج |
| `user_panel` | `panel_service` | پنل + داشبورد |
| `user_profile` | `user_profile_service` | پروفایل مستقل |
| `account_setting` | `account_setting_service` | تنظیمات حساب |
| `home` | — | صفحه لندینگ |

---

## ۶. سیستم دسترسی (Access Control)

### ۶.۱. مدل ذهنی

سیستم دسترسی بر اساس **چهار جدول** کار می‌کند:

| جدول | نقش |
|---|---|
| `role` | لیست نقش‌ها (admin, manager, user, guest) |
| `form` | هر چیزی که باید چک شود (صفحه، partial، فیلد، دکمه) |
| `condition_of` | سطوح دسترسی: `Closed`, `Low`, `Medium`, `High`, `Full` |
| `form_access` | اتصال (role × form) با یک condition |

### ۶.۲. قواعد کلیدی

- **`Closed`** یعنی دسترسی کاملاً بسته است، صرف‌نظر از هر چیز دیگری.
- **`required_condition`** اگر `None` باشد، هر شرطی جز Closed قبول است.
- **`guest`** نقش کاربران ناشناس است. برای صفحات عمومی استفاده می‌شود.
- **Cache:** `AccessChecker` نتایج را با TTL نگه می‌دارد:
  - `enabled` کاربر: ۱۵ ثانیه
  - `role` کاربر: ۶۰ ثانیه
  - `role → form`: ۳۰۰ ثانیه

### ۶.۳. API عمومی

```python
db_service.has_access(user_id, form_id, required_condition=None) -> bool
db_service.get_form_condition(user_id, form_id) -> str | None
db_service.get_accessible_forms(user_id) -> list[str]
db_service.has_public_access(form_id, required_condition=None) -> bool
db_service.invalidate_access_cache(user_id=None)
db_service.invalidate_role_cache(role_id=None)
db_service.invalidate_form_cache(form_id=None)
```

---

## ۷. کامپوننت‌های Web

### ۷.۱. لیست کامل

| کامپوننت | نقش |
|---|---|
| `<ramz-brand>` | لوگو + نام برند |
| `<ramz-promo>` | کارت تبلیغاتی |
| `<ramz-card>` | کارت پایه با slot (icon, header-actions, footer) |
| `<ramz-topbar>` | Topbar برای صفحات مستقل (fixed، با slot های hamburger/actions/center) |
| `<ramz-sidebar>` | سایدبار پنل با collapse/drawer |
| `<ramz-menu-group>` | گروه‌بندی منوها |
| `<ramz-menu-item>` | آیتم منو با badge و endpoint |
| `<ramz-collapse-btn>` | دکمه collapse سایدبار |
| `<ramz-hamburger-btn>` | دکمه باز کردن drawer |
| `<ramz-search>` | جستجو با دو حالت (inline, modal) |
| `<ramz-notifications>` | پنل اعلان‌ها |
| `<ramz-user-menu>` | منوی کشویی کاربر |
| `<content-container>` | کانتینر AJAX با loading/error states |
| `<ramz-progress-bar>` | نوار پیشرفت لود |
| `<ramz-coin-watchlist>` | جدول واچ‌لیست |
| `<ramz-dialog>` | Dialog سراسری (ask/confirm/alert/passwordConfirm) |

### ۷.۲. قواعد نوشتن کامپوننت

```javascript
// همه کامپوننت‌ها:
// ۱. HTMLElement بومی (بدون Lit)
// ۲. Light DOM (بدون Shadow DOM)
// ۳. createRenderRoot() -> this (اگر از Lit استفاده نمی‌شود، این خط حذف می‌شود)
// ۴. نام‌گذاری: ramz-*
// ۵. نام فایل: kebab-case

import { defineComponent, attr, emit, escapeHtml } from '../_base.js';

class RamzSomething extends HTMLElement {
  static get observedAttributes() { return ['some-attr']; }

  #state = null;
  #refs  = {};

  connectedCallback() {
    this._render();
    this._cacheRefs();
    this._attachListeners();
  }

  disconnectedCallback() {
    this._detachListeners();
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal || !this.isConnected) return;
    this._render();
    this._cacheRefs();
  }

  _render()          { this.innerHTML = `...`; }
  _cacheRefs()       { /* ذخیره reference */ }
  _attachListeners() { /* ثبت listener */ }
  _detachListeners() { /* حذف listener */ }
}

defineComponent('ramz-something', RamzSomething);
```

### ۷.۳. sync متمرکز کامپوننت‌ها

```javascript
// broadcast از هر جای کد:
import { broadcastUserUpdate } from '../_base.js';
broadcastUserUpdate({ name: 'New Name', email: 'new@x.com', initials: 'NN' });

// در کامپوننت: listener
window.addEventListener('ramz:user-updated', (e) => {
  this.setUser(e.detail);
});
```

---

## ۸. سیستم طراحی (style.css)

### ۸.۱. ساختار بخش‌ها

`app/template_service/static/css/style.css` شامل ۲۶ بخش:

1. Reset & Base
2. Design Tokens (CSS Variables)
3. Decorative Orbs
4. Shared Utilities (Avatars, Icon Tiles, Buttons)
5. Landing Page
6. Login Page
7. Auth Error States
8. Error Page
9. Dashboard Shell
10. Sidebar
11. Main Area & Topbar
12. Search
13. Icon Buttons & Dropdowns
14. Content Area
15. Card Component
16. Stats Grid
17. Panels Grid
18. Chart
19. Activity List
20. Table / Watchlist
21. Mobile Overlay
22. Search Modal
23. Content Container
24. Custom Element Hooks
25. Responsive
26. Reduced Motion

بخش‌های اضافه‌شده در جریان کار:
- **Standalone Pages** (topbar, content, profile hero, two-col)
- **Settings Layout** (nav, content, rows, fields, toggle, banking, channel list, cascade dialog)
- **Top Progress Bar**

### ۸.۲. توکن‌های کلیدی

```css
--glass-bg: linear-gradient(...);
--glass-border: 1px solid rgba(255,255,255,0.09);
--glass-blur: blur(22px) saturate(150%);
--primary: #6366f1;
--violet:  #a855f7;
--text:    #e8edf7;
--text-dim:#a3aec4;
--muted:   #7b87a1;
--radius:  16px;
```

---

## ۹. Schema پایگاه داده (v4.1)

### ۹.۱. جداول

| گروه | جداول |
|---|---|
| **Lookup** | `role`, `condition_of`, `form`, `bank`, `subscription`, `activity_type`, `address_type`, `phone_type` |
| **Core Contact Hub** | `contact` |
| **People** | `people` |
| **Users** | `user`, `user_activity_log`, `form_access`, `user_session` |
| **Contact Info** | `phone`, `post_address`, `email` |
| **Banking** | `bank_account`, `bank_card` |

### ۹.۲. الگوهای کلیدی

- **Contact-People-User:** `contact` به‌عنوان hub، `people` اطلاعات هویتی، `user` اطلاعات ورود.
- **چند-مقداری:** `email`, `phone`, `post_address`, `bank_account` همه one-to-many از `contact`.
- **Primary pointers:** `user.email_id`, `user.phone_id` اشاره به رکورد اصلی می‌کنند.
- **Banking nested:** `bank_card` زیر `bank_account` (cascade delete).
- **Soft delete:** `enabled` ستون در همه جداول مهم.
- **Referential integrity:** FK با `ON DELETE CASCADE` برای جداول وابسته به `contact`.

### ۹.۳. داده‌های پیش‌فرض

| جدول | داده |
|---|---|
| `role` | admin, manager, user, guest |
| `condition_of` | Closed, Low, Medium, High, Full |
| `subscription` | free, basic, premium, enterprise |
| `activity_type` | login, logout, password_change, profile_update, 2fa_enabled, 2fa_disabled, subscription_change, signup |
| `address_type` | home, work, billing, shipping |
| `phone_type` | mobile, home, work, fax |

### ۹.۴. seed های جداگانه

- `data/seed_auth.sql` — فرم‌های auth و دسترسی guest
- `data/seed_user_profile.sql` — فرم‌های profile
- `data/seed_account_setting.sql` — ۷ فرم تنظیمات

**فلسفه:** هیچ داده‌ای در کد ماژول seed نمی‌شود. همه از طریق SQL خارجی.

---

## ۱۰. Workflows اصلی

### ۱۰.۱. ورود

```
POST /login
  → auth_service.login(username, password, request)
    → login_workflow.login_strict
      → user_repository.get_by_username (include_password=True)
      → بررسی enabled
      → verify_password (bcrypt)
      → اگر needs_rehash: update_password_hash
      → activity_repository.log("login")
      → session_repository.create()
      → user.password_hash = None
  → build_session_user → request.session["user"]
  → request.session["session_id"] = ...
  → redirect به /panel
```

### ۱۰.۲. ثبت‌نام

```
POST /signup
  → چک has_public_access("auth.signup.view")
  → اعتبارسنجی فرم
  → db_service.create_account(SignupData)
    → signup_workflow.create_account
      → pre-checks (username, email)
      → resolve role (default: "user")
      → hash_password (خارج از transaction)
      → BEGIN TRANSACTION:
          contact → people → email → phone → user
      → activity_repository.log("signup")
  → auto-login
  → redirect به /panel
```

### ۱۰.۳. پروفایل

```
GET /profile
  → چک session
  → db_service.get_full_profile(user_id)
  → activities + activity_count
  → render profile.html
```

### ۱۰.۴. تنظیمات

```
GET /account/settings?section=personal
  → render shell (topbar + nav + content-container)
  → content-container لود می‌کند: POST /account/settings/partials/personal
     → render partial

POST /account/settings/personal
  → _ensure_authenticated (چک session + revoked + enabled)
  → چک has_access("account.profile.edit")
  → db_service.update_personal_info(user_id, data)
  → _refresh_session
  → JSON response
```

### ۱۰.۵. حذف Session

```
POST /account/settings/sessions/revoke
  → چک has_access("account.sessions.manage")
  → چک password
  → verify_current_user_password
  → session_repository.revoke(session_id)
  → invalidate_validity_cache
  → JSON success
```

### ۱۰.۶. Eject خودکار session

```
هر درخواست به صفحات محافظت‌شده
  → _check_session / _ensure_authenticated
    → is_user_enabled (TTL 15s)
    → is_session_valid (TTL 15s، از cache)
  → اگر revoked شد:
     • HTML: redirect به /
     • AJAX: 401 JSON با {status: "session_revoked"}
  → fetch interceptor در سمت کاربر redirect می‌کند
```

---

## ۱۱. تأیید رمز برای اقدامات حساس

### ۱۱.۱. لیست اقدامات حساس

| اقدام | پیشوند |
|---|---|
| افزودن/ویرایش/حذف حساب بانکی | `banking/accounts/*` |
| افزودن/ویرایش/حذف کارت بانکی | `banking/cards/*` |
| فعال/غیرفعال حساب/کارت | `banking/*/toggle` |
| Revoke session | `sessions/revoke` |
| Revoke all other sessions | `sessions/revoke-others` |

### ۱۱.۲. جریان

1. کاربر روی دکمه کلیک می‌کند.
2. **اگر حذف است:** `appDialog.confirm` برای تأیید
3. `appDialog.passwordConfirm` — dialog با input پسورد
4. اگر لغو → هیچ تغییری
5. اگر تأیید → `FormData` با `password`
6. سرور: `_require_password` — verify با bcrypt
7. اگر اشتباه → `appDialog.alert` قرمز "Action not allowed"

### ۱۱.۳. UI — کامپوننت `ramz-dialog`

```javascript
// تأیید ساده
await appDialog.confirm({ title, message, confirmLabel, cancelLabel, variant, icon });

// اطلاع‌رسانی
await appDialog.alert({ title, message, closeLabel, icon });

// چند دکمه‌ای
await appDialog.ask({ title, desc, buttons: [{ value, label, variant }] });

// تأیید با پسورد
const password = await appDialog.passwordConfirm({
  title: 'Confirm with password',
  message: '...',
  confirmLabel: 'Confirm',
  icon: 'lock',
});
// password === null اگر لغو شد
```

---

## ۱۲. الگوهای توسعه

### ۱۲.۱. قواعد ثابت

| قاعده | توضیح |
|---|---|
| **بدون Lit** | همه کامپوننت‌ها `HTMLElement` بومی |
| **بدون Shadow DOM** | همه استایل‌ها در `style.css` سراسری |
| **بدون import مستقیم FastAPI** | همه چیز از `context.services` |
| **رویدادها با پیشوند `ramz:`** | namespace متمرکز |
| **تگ‌ها با پیشوند `ramz-`** | kebab-case |
| **`requires` به نام سرویس** | نه نام ماژول |
| **`component_service` مالک کامپوننت‌ها** | ماژول `ui_components` |
| **`app_db_service` مالک داده** | ماژول `db_manager` |
| **`style.css` سراسری** | ماژول `template_service` |
| **بدون seed در کد** | فقط SQL خارجی |
| **همه پیام‌های modal از `ramz-dialog`** | بدون `window.confirm` |
| **همه پیام‌های inline از `.settings-flash`** | warning / success / error |
| **همه صفحات بسته → error page** | از طریق `_render_closed_page` |

### ۱۲.۲. الگوی Repository

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

### ۱۲.۳. الگوی Workflow

```python
class XWorkflow:
    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    async def do_something(self, user_id, ...):
        # ۱. چک‌های pre-flight (بدون DB یا با DB read)
        # ۲. تراکنش اتمیک برای عملیات چند-جدولی
        # ۳. activity log (best-effort)
        # ۴. برگرداندن نتیجه
```

### ۱۲.۴. الگوی Route در account_setting

```python
@http_api.post("/account/settings/xxx/yyy", response_class=http_api.HTMLResponse)
async def xxx_yyy(request: http_api.Request):
    # ۱. auth + session
    user_id, redirect = await _ensure_authenticated(request)
    if redirect:
        return redirect

    # ۲. access check
    try:
        allowed = await db_service.has_access(user_id, "account.xxx")
    except Exception:
        allowed = False
    if not allowed:
        return _json_error("no_permission", "...")

    # ۳. form + password
    form = await request.form()
    err = await _require_password(form, user_id)
    if err:
        return err

    # ۴. business logic
    ...

    # ۵. response
    return _json_ok("...", section="xxx", reload_section=True)
```

---

## ۱۳. الگوهای فرانت‌اند

### ۱۳.۱. AJAX partial loading

```
<form method="post" action="/account/settings/xxx" data-ajax="true">
```

Handler عمومی در `settings.html`:
1. تشخیص `data-require-password="true"`
2. اگر لازم: confirm + passwordConfirm
3. `fetch` با `Accept: application/json`
4. پاسخ `{status, message, section, reload_section, user_update, code}`

### ۱۳.۲. Search Dropdown

- دسکتاپ: پیوست به input
- موبایل: modal تمام‌صفحه
- دو حالت از یک کامپوننت

### ۱۳.۳. Progress Bar

- در `topbar` با attribute `show-progress`
- رویداد `ramz:content-loading` / `ramz:content-loaded`
- برای هر دو AJAX لود و Save استفاده می‌شود

### ۱۳.۴. Session Revoked Interceptor

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

## ۱۴. قواعد Idempotency و Migration

### ۱۴.۱. `create_db.sql`

- **کاملاً Idempotent**
- همه `CREATE TABLE IF NOT EXISTS`
- همه `CREATE INDEX IF NOT EXISTS`
- همه `INSERT OR IGNORE`
- هرگز چیزی را DROP یا ALTER نمی‌کند

### ۱۴.۲. Migration ها

فایل‌های `data/migration_*.sql`:
- یک‌بارمصرف
- با `PRAGMA foreign_keys = OFF`
- با `BEGIN TRANSACTION` و `COMMIT`
- پشتیبان‌گیری قبلی توصیه می‌شود

### ۱۴.۳. seed ها

- `seed_*.sql` برای داده‌های موردنیاز ماژول‌ها
- Idempotent با `INSERT OR IGNORE`
- ادمین مسئول اجراست

---

## ۱۵. قواعد نام‌گذاری

| مورد | قاعده | مثال |
|---|---|---|
| تگ کامپوننت | `ramz-*` | `ramz-card` |
| نام فایل JS | kebab-case | `notification-panel.js` |
| کلاس JS | PascalCase با `Ramz` | `RamzNotificationPanel` |
| Attribute | kebab-case | `user-name`, `card-class` |
| رویداد سفارشی | `ramz:*` | `ramz:load-content` |
| کلاس CSS | kebab-case | `.card-head-left` |
| متد خصوصی JS | `_` prefix | `_render`, `_cacheRefs` |
| Field خصوصی JS | `#` prefix | `#open` |
| نام سرویس | snake_case | `app_db_service` |
| نام ماژول | snake_case | `user_panel` |
| فرم ID | dotted | `account.profile.edit` |
| Route | kebab-case | `/account/settings/personal` |

---

## ۱۶. وضعیت فعلی و کارهای باقی‌مانده

### ۱۶.۱. تکمیل‌شده

- ✅ انتقال کامل به Nebula theme
- ✅ حذف Lit → HTMLElement بومی
- ✅ ماژول `ui_components` با ۱۶ کامپوننت
- ✅ بازسازی کامل `db_manager` (فازهای ۱–۱۳)
- ✅ `user_profile` با صفحه پروفایل کامل
- ✅ `account_setting` با ۸ partial AJAX
- ✅ Session management با revoke + auto-eject
- ✅ Banking چند-حساب و چند-کارت
- ✅ Multi-channel contacts (email, phone, address)
- ✅ سیستم Access Control با cache
- ✅ `ramz-dialog` سراسری
- ✅ Progress bar در topbar
- ✅ Password confirm برای اقدامات حساس
- ✅ Error page استاندارد برای صفحات بسته
- ✅ Schema idempotent v4.1 با FK ها

### ۱۶.۲. باقی‌مانده

| مورد | توضیح |
|---|---|
| **2FA کامل** | تولید TOTP secret + QR code + verify |
| **Password reset** | فراموشی رمز با ایمیل |
| **Email verification** | تأیید ایمیل با لینک |
| **Phone verification** | تأیید تلفن با SMS |
| **Subscription management** | Change plan و پرداخت |
| **Delete account** | حذف با تأیید دو مرحله‌ای |
| **Billing** | مدیریت فاکتورها |
| **Admin panel** | مدیریت users، roles، forms |
| **Analytics pages** | صفحات analytics, predictions, markets, portfolio, alerts |
| **Landing/Signup social** | ورود با Google/GitHub |
| **i18n** | چند زبانه |
| **Notification center** | سیستم اعلان کامل |

---

## ۱۷. نکات مهم برای توسعه‌دهنده بعدی

1. **هرگز Lit اضافه نکنید.** معماری به HTMLElement بومی گره خورده است.
2. **هرگز Shadow DOM اضافه نکنید.** همه استایل‌ها باید از `style.css` سراسری بیایند.
3. **همیشه از `_base.js` helperها استفاده کنید.** `attr`, `emit`, `escapeHtml`.
4. **همیشه `data-ajax="true"` برای فرم‌های تنظیمات.** handler عمومی همه چیز را مدیریت می‌کند.
5. **همیشه `data-require-password="true"` برای اقدامات حساس.**
6. **همیشه `_ensure_authenticated` را در ابتدای route صدا بزنید.**
7. **همیشه `reload_section=True` در JSON response بعد از تغییرات.**
8. **هرگز `window.confirm` / `window.alert` استفاده نکنید.** فقط `appDialog`.
9. **همه seed ها در `data/*.sql`، نه در کد.**
10. **همه migration ها یک‌بارمصرف با پشتیبان‌گیری.**

---

## ۱۸. جمع‌بندی

پروژه Ramz یک اپلیکیشن وب ماژولار است که:

- **معماری تمیز و لایه‌ای** دارد (repositories → workflows → services → routes).
- **کامپوننت‌محور** است (۱۶ کامپوننت مستقل).
- **سیستم دسترسی سطح‌بالا** دارد (۴ جدول + cache).
- **قابل نگهداری** است (schema idempotent، seed های جداگانه).
- **امن** است (bcrypt، session tracking، password confirm، eject خودکار).

**وضعیت فعلی:** پایدار برای توسعه بیشتر.  
**ریسک نگهداری:** پایین (معماری مستند و یکدست).  
**آماده برای فاز بعدی:** ✅

---

**تاریخ به‌روزرسانی:** ۱۴۰۴/۰۷/۲۵  
**وضعیت:** پایدار، آماده برای توسعه صفحات جدید  
**مرجع اصلی:** این سند