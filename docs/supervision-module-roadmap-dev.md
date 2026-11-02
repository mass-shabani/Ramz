# راهنمای توسعه و نقشه راه ماژول Supervision — Ramz

```markdown
# نقشهٔ راه و راهنمای توسعه — ماژول Supervision

> **نسخهٔ سند:** 1.0
> **وضعیت فعلی پروژه:** Gen 2 کامل (Admin Panel), Schema v10.0
> **هدف این سند:** راهنمای جامع و عملیاتی برای توسعه‌دهنده (انسانی یا AI)
> **پیش‌نیازها:** خواندن `task-prompt.md`, `initial-review-report-v2.md`, `docs/access-control.md`

---

## فهرست

1. [خلاصهٔ اجرایی](#۱-خلاصهٔ-اجرایی)
2. [هدف و دامنه](#۲-هدف-و-دامنه)
3. [چرا ماژول مستقل؟](#۳-چرا-ماژول-مستقل)
4. [مدل دسترسی](#۴-مدل-دسترسی)
5. [معماری کلی](#۵-معماری-کلی)
6. [ساختار دایرکتوری](#۶-ساختار-دایرکتوری)
7. [تغییرات Schema (v10 → v11)](#۷-تغییرات-schema-v10--v11)
8. [Seeds و Migrations](#۸-seeds-و-migrations)
9. [قرارداد Routes و API](#۹-قرارداد-routes-و-api)
10. [طراحی UI/Layout](#۱۰-طراحی-uilayout)
11. [لایهٔ Service و منطق](#۱۱-لایهٔ-service-و-منطق)
12. [سیستم Audit Trail (deep dive)](#۱۲-سیستم-audit-trail-deep-dive)
13. [ثبت Extension](#۱۳-ثبت-extension)
14. [نقشهٔ راه فازها (T76.1 → T76.5)](#۱۴-نقشهٔ-راه-فازها)
15. [فاز ۱: Foundation (T76.1.1 + T76.1.2)](#۱۵-فاز-۱-foundation)
16. [فاز ۲: Activity Viewer (T76.2)](#۱۶-فاز-۲-activity-viewer)
17. [فاز ۳: Health Dashboard (T76.3)](#۱۷-فاز-۳-health-dashboard)
18. [فاز ۴: Audit Trail (T76.4.1 + T76.4.2)](#۱۸-فاز-۴-audit-trail)
19. [فاز ۵: Polish و Close (T76.5)](#۱۹-فاز-۵-polish-و-close)
20. [نگرانی‌های عرضی](#۲۰-نگرانی‌های-عرضی)
21. [دام‌های رایج](#۲۱-دام‌های-رایج)
22. [الزامات مستندسازی](#۲۲-الزامات-مستندسازی)
23. [چک‌لیست تحویل](#۲۳-چک‌لیست-تحویل)
24. [معیارهای پذیرش نهایی](#۲۴-معیارهای-پذیرش-نهایی)

---

## ۱. خلاصهٔ اجرایی

**Supervision** یک ماژول مستقل Ramz است که **مشاهده‌پذیری سیستم-wide** (system-wide observability) و **قابلیت audit** را برای نقش‌های `admin`, `manager`, `super-admin` فراهم می‌کند.

**سه هدف اصلی:**

1. **Activity Log Viewer** — دیدن فعالیت همهٔ کاربران با فیلترهای پیشرفته
2. **System Health Dashboard** — وضعیت لحظه‌ای DB، sessions، activity rate
3. **Audit Trail** — ثبت خودکار همهٔ اقدامات admin برای accountability

**مکان:** `/supervision` (namespace مستقل، نه زیر `admin_panel`)

**مدت تخمینی:** ۵ فاز، ۷ تسک، حدود ۳–۵ روز کاری

**خروجی نهایی:** ماژول کاملاً مستقل، قابل فعال/غیرفعال بدون تأثیر روی `admin_panel`

---

## ۲. هدف و دامنه

### ۲.۱. اهدافی که در دامنه است (In Scope)

| قابلیت | اولویت | فاز |
|---|---|---|
| ماژول skeleton (shell, layout, nav) | حیاتی | T76.1 |
| Activity log viewer با فیلتر | حیاتی | T76.2 |
| Health dashboard (DB, sessions, activity) | حیاتی | T76.3 |
| Audit trail (schema + logging + viewer) | حیاتی | T76.4 |
| Extension registration (user menu link) | حیاتی | T76.1 |
| مستندات کامل | حیاتی | T76.5 |

### ۲.۲. اهدافی که خارج از دامنه است (Out of Scope)

| قابلیت | دلیل |
|---|---|
| Real-time monitoring / websocket | فاز آینده — MVP polling کافی است |
| Export CSV/PDF از activity/audit | فاز آینده (per-button forms در seed رزرو شده) |
| Purge/delete activity logs (retention policy) | فاز آینده — نیازمند background task |
| Alerting / notifications از health | فاز آینده — نیازمند event system |
| User-level session termination از supervision | فاز آینده — `account_setting` دارد |
| Role/User/Form CRUD از داخل supervision | این‌ها در `admin_panel` هستند |
| System settings (system-admin) | ماژول جداگانه (`system_settings`) |

### ۲.۳. اصل طراحی

> **Supervision = مشاهدهٔ سیستم، بدون تغییر آن.**

Supervision یک **read-only observability module** است. هیچ‌گاه داده‌ای را تغییر نمی‌دهد. تنها استثنا: `admin_action_log` که به‌طور خودکار از side-effect اقدامات admin_panel پر می‌شود (نه از خود supervision).

---

## ۳. چرا ماژول مستقل؟

سه دلیل اصلی:

1. **دسترسی متفاوت** — Supervision برای admin + manager + super-admin است. Admin Panel همچنین. اما هم‌پوشانی کامل نیست: اگر روزی manager از admin_panel محروم شود، supervision باید همچنان برایش باز باشد.

2. **دامنهٔ متفاوت** — Admin Panel = مدیریت کاربران/فرم/گرنت/نقش. Supervision = مشاهدهٔ سیستم‌wide. این‌ها دو نوع فعالیت متفاوت‌اند (mutating vs read-only).

3. **قابلیت فعال/غیرفعال مستقل** — در `app_settings.json` می‌توان یکی را بدون دیگری فعال/غیرفعال کرد.

**پیامد مهم:** هیچ import مستقیمی بین `admin_panel` و `supervision` وجود ندارد. تنها ارتباط: audit logging که از `admin_panel` به `db_manager` می‌رود و در `supervision` فقط نمایش داده می‌شود.

---

## ۴. مدل دسترسی

### ۴.۱. فرم‌های section (4)

| form_id | gate |
|---|---|
| `supervision.view` | دیدن "Supervision" در user menu + ورود به `/supervision` |
| `supervision.activity.view` | دیدن بخش Activity |
| `supervision.health.view` | دیدن بخش Health |
| `supervision.audit.view` | دیدن بخش Audit |

### ۴.۲. فرم‌های action (رزرو — برای فاز آینده)

| form_id | کاربرد آینده |
|---|---|
| `supervision.activity.export` | export CSV |
| `supervision.audit.export` | export CSV |
| `supervision.activity.purge` | حذف logs قدیمی |

**این‌ها در seed v1.0 ایجاد می‌شوند اما هیچ‌جا استفاده نمی‌شوند** — فقط آماده‌سازی برای فاز آینده.

### ۴.۳. Grants (seed v1.0)

| Role | supervision.view | activity.view | health.view | audit.view |
|---|---|---|---|---|
| `super-admin` | ✅ | ✅ | ✅ | ✅ |
| `manager` | ✅ | ✅ | ✅ | ✅ |
| `admin` | ✅ | ✅ | ✅ | ✅ |
| `system-admin` | ❌ | ❌ | ❌ | ❌ (رزرو) |

همه در `level=1`.

**توجه:** No rank filter در supervision. چون read-only است، مشاهدهٔ داده‌های همهٔ کاربران مجاز است.

---

## ۵. معماری کلی

```
┌──────────────────────────────────────────────────────────┐
│  Browser                                                 │
│  /supervision + supervision_layout.html + JS             │
└──────────────────────────────────────────────────────────┘
              │ HTTP (shell + partial + JSON)
              ▼
┌──────────────────────────────────────────────────────────┐
│  supervision module                                      │
│  ├── module.py       (registration)                      │
│  ├── routes.py       (shell + partial + JSON endpoints)  │
│  ├── services.py     (business logic: stats, filters)    │
│  └── templates/                                          │
│      ├── supervision_layout.html                         │
│      └── partials/{overview,activity,health,audit}.html  │
└──────────────────────────────────────────────────────────┘
              │ context.services
              ▼
┌──────────────────────────────────────────────────────────┐
│  db_manager (Facade + Repositories + Workflows)          │
│  ├── app_db_service                                      │
│  ├── audit_workflow           ← NEW (T76.4)              │
│  └── admin_action_repository  ← NEW (T76.4)              │
└──────────────────────────────────────────────────────────┘
              │
              ▼
system_database → SQLite (v11.0)
```

**نکتهٔ مهم:** Supervision از `db_service` موجود استفاده می‌کند. تنها اضافه‌های لازم: `admin_action_repository` + `audit_workflow` (که در T76.4.1 اضافه می‌شوند).

---

## ۶. ساختار دایرکتوری

### ۶.۱. ساختار نهایی (پس از T76.5)

```
app/
└── supervision/
    ├── manifest.json
    ├── module.py
    ├── routes.py
    ├── services.py
    └── templates/
        ├── supervision_layout.html
        └── partials/
            ├── overview.html
            ├── activity.html
            ├── health.html
            ├── audit.html
            └── coming-soon.html

db_scripts/
├── seed_supervision.v1.0.sql   ← NEW (T76.1.1)
├── create_db.v10.1.sql         ← NEW (T76.1.1, data only)
├── create_db.v11.0.sql         ← NEW (T76.4.1, schema + data)
└── migration_v10_to_v11.sql    ← NEW (T76.4.1, admin_action_log)

app/db_manager/
├── repositories/
│   └── admin_action_repository.py   ← NEW (T76.4.1)
└── workflows/
    └── audit_workflow.py            ← NEW (T76.4.1)

docs/
├── supervision-roadmap.md           ← این سند
└── supervision.md                   ← NEW (T76.5, reference)
```

### ۶.۲. `manifest.json`

```json
{
  "name": "supervision",
  "version": "1.0.0",
  "enabled": true,
  "entrypoint": "SupervisionModule",
  "description": "System-wide observability: activity log viewer, health dashboard, audit trail.",
  "requires": [
    "core_logger",
    "http_api",
    "template_service",
    "app_db_service",
    "message_service",
    "component_service"
  ],
  "provides": ["supervision_service"]
}
```

---

## ۷. تغییرات Schema (v10 → v11)

### ۷.۱. v10 → v10.1 (بدون schema change — فقط داده)

T76.1.1 فقط دادهٔ supervision را اضافه می‌کند. **هیچ جدول جدیدی.** پس migration نیاز نیست.

### ۷.۲. v10.1 → v11.0 (schema change در T76.4.1)

جدول جدید `admin_action_log`:

```sql
CREATE TABLE IF NOT EXISTS admin_action_log (
    action_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id     INTEGER NOT NULL,
    action       TEXT NOT NULL,
    entity_type  TEXT,
    entity_id    TEXT,
    old_value    TEXT,
    new_value    TEXT,
    ip_address   TEXT,
    user_agent   TEXT,
    success      INTEGER NOT NULL DEFAULT 1 CHECK(success IN (0, 1)),
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES user(user_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_action_log_admin_id
    ON admin_action_log(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_action_log_timestamp
    ON admin_action_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_admin_action_log_entity
    ON admin_action_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_admin_action_log_action
    ON admin_action_log(action);
```

**نکات طراحی:**

- `entity_id TEXT` — نه INTEGER. چون form_id (TEXT) و role_id (TEXT) و user_id (INTEGER) همه در این ستون می‌آیند. ذخیره به‌صورت string + cast در خواندن.
- `old_value` / `new_value` = JSON strings — flexible per-action shape
- `success` — ثبت اقدامات ناموفق هم مفید است (debug + security)
- `ON DELETE SET NULL` — اگر admin حذف شد، log باقی می‌ماند
- `timestamp` — server time, نه client

### ۷.۳. Migration `migration_v10_to_v11.sql`

```sql
-- Back up data/rmz_data.db before running!
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS admin_action_log (...);
-- indexes...

COMMIT;
PRAGMA foreign_keys = ON;
```

**⚠️ Not idempotent** — فقط یک‌بار اجرا شود (اگر جدول از قبل موجود است، `IF NOT EXISTS` از خطا جلوگیری می‌کند اما rollback ندارد).

---

## ۸. Seeds و Migrations

### ۸.۱. `seed_supervision.v1.0.sql` (T76.1.1)

```sql
-- Requires: create_db.v10.0 or v10.1 or migrated v11
-- IDEMPOTENT

PRAGMA foreign_keys = ON;

-- Forms
INSERT OR IGNORE INTO form (form_id, form_name, description) VALUES
('supervision.view',                'Supervision Access',       'Access to /supervision'),
('supervision.activity.view',       'View Activity Log',        'Access the Activity section'),
('supervision.health.view',         'View System Health',       'Access the Health section'),
('supervision.audit.view',          'View Audit Trail',         'Access the Audit section'),
-- Reserved for future (not used yet):
('supervision.activity.export',     'Export Activity Log',      'Download activity as CSV'),
('supervision.audit.export',        'Export Audit Trail',       'Download audit as CSV'),
('supervision.activity.purge',      'Purge Activity Log',       'Delete old activity entries');

-- Grants (level=1)
INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
-- super-admin
('super-admin', 'supervision.view', 1),
('super-admin', 'supervision.activity.view', 1),
('super-admin', 'supervision.health.view', 1),
('super-admin', 'supervision.audit.view', 1),

-- manager
('manager', 'supervision.view', 1),
('manager', 'supervision.activity.view', 1),
('manager', 'supervision.health.view', 1),
('manager', 'supervision.audit.view', 1),

-- admin
('admin', 'supervision.view', 1),
('admin', 'supervision.activity.view', 1),
('admin', 'supervision.health.view', 1),
('admin', 'supervision.audit.view', 1);
```

### ۸.۲. `create_db.v10.1.sql` (T76.1.1)

کپی از `create_db.v10.0.sql` + افزودن supervision forms/grants به بلوک‌های `INSERT INTO form` و `INSERT INTO form_access`.

**⚠️ هدر version را به `10.1` تغییر بده و changelog را آپدیت کن.**

### ۸.۳. `create_db.v11.0.sql` (T76.4.1)

کپی از `v10.1` + افزودن `CREATE TABLE admin_action_log` و indexها.

### ۸.۴. `migration_v10_to_v11.sql` (T76.4.1)

فقط جدول `admin_action_log` و indexها. بقیهٔ schema دست‌نخورده.

---

## ۹. قرارداد Routes و API

### ۹.۱. Shell + Partials

| Method | Path | Response | Grant |
|---|---|---|---|
| GET | `/supervision` | HTML shell | `supervision.view` |
| POST | `/supervision/partials/{section}` | HTML partial | `supervision.view` + section grant |

`section` ∈ `{overview, activity, health, audit}`.

### ۹.۲. JSON endpoints

| Method | Path | Purpose | Grant |
|---|---|---|---|
| POST | `/supervision/activity/list` | Activity rows (filter + pagination) | `supervision.activity.view` |
| POST | `/supervision/activity/users` | User dropdown options | `supervision.activity.view` |
| POST | `/supervision/activity/types` | Activity type dropdown options | `supervision.activity.view` |
| POST | `/supervision/health/stats` | Health metrics | `supervision.health.view` |
| POST | `/supervision/audit/list` | Audit rows (filter + pagination) | `supervision.audit.view` |
| POST | `/supervision/audit/admins` | Admin dropdown options | `supervision.audit.view` |

### ۹.۳. Request/Response shapes

#### `POST /supervision/activity/list`

Request:
```json
{
  "user_id": 5,
  "activity_type": "login",
  "date_from": "2026-10-01",
  "date_to": "2026-10-31",
  "success": true,
  "offset": 0,
  "limit": 50
}
```
همه فیلترها optional.

Response:
```json
{
  "columns": [
    {"key": "_user",   "label": "User", "type": "avatar"},
    {"key": "type",    "label": "Type"},
    {"key": "ip",      "label": "IP", "className": "mono"},
    {"key": "success", "label": "Result", "type": "badge"},
    {"key": "time",    "label": "Time", "type": "date"}
  ],
  "rows": [
    {
      "_user": {"initials":"AS","name":"Alice Smith","email":"...","avatarClass":"avatar--indigo"},
      "type": "login",
      "ip": "1.2.3.4",
      "success": {"text": "Success", "variant": "active"},
      "time": "2026-10-30T12:00:00",
      "_raw": {...}
    }
  ],
  "total": 1234,
  "offset": 0,
  "limit": 50
}
```

#### `POST /supervision/health/stats`

Response:
```json
{
  "db": {
    "size_bytes": 204800,
    "tables": {
      "user": 15, "people": 15, "contact": 15,
      "form": 39, "form_access": 90, "role": 8,
      "user_session": 5, "user_activity_log": 456,
      "admin_action_log": 78
    }
  },
  "sessions": {
    "total_active": 5,
    "by_role": {"admin": 2, "user": 3}
  },
  "activity": {
    "last_hour": 12,
    "last_day": 234,
    "last_week": 1523
  },
  "login": {
    "failed_last_hour": 3,
    "failed_last_day": 18
  },
  "system": {
    "server_time": "2026-10-30T12:00:00",
    "db_type": "sqlite",
    "uptime_note": "SQLite single-file"
  }
}
```

#### `POST /supervision/audit/list`

Request:
```json
{
  "admin_id": 5,
  "action": "set_user_role",
  "entity_type": "user",
  "date_from": "2026-10-01",
  "date_to": "2026-10-31",
  "success": true,
  "offset": 0,
  "limit": 50
}
```

Response: مشابه activity/list با ستون‌های:
- admin (avatar)
- action (badge/text)
- entity (text: "user #5")
- success (badge)
- time (date)

---

## ۱۰. طراحی UI/Layout

### ۱۰.۱. `supervision_layout.html` — الگو

**الگو:** مشابه `admin_layout.html` (topbar + settings-nav + content-container). **نه** sidebar-based (که `user_panel` دارد). دلیل: supervision یک admin tool است، نه یک user workspace.

```html
{% extends "base.html" %}

{% block body_class %}page-dashboard{% endblock %}

{% block content %}
<div class="app" style="display: block;">
  <div class="main" style="width: 100%;">

    <ramz-topbar
      user-name="{{ profile.full_name }}"
      user-email="{{ profile.email or '' }}"
      user-initials="{{ profile.initials }}"
      show-progress
    ></ramz-topbar>

    <main class="standalone-content">

      <div class="page-head">
        <div>
          <h1>Supervision</h1>
          <p>System-wide observability and audit.</p>
        </div>
        <a class="btn-ghost" href="/settings/admin">
          Back to Admin Panel
        </a>
      </div>

      <div class="settings-layout">

        <aside class="settings-nav" id="supervisionNav">
          <div class="settings-nav-title">Supervision</div>

          <a class="settings-nav-item {% if section == 'overview' %}active{% endif %}"
             href="?section=overview"
             data-section="overview"
             data-endpoint="/supervision/partials/overview">
            <span class="settings-nav-icon">
              <svg viewBox="0 0 24 24" ...>...</svg>
            </span>
            Overview
          </a>

          {% if permissions.activity %}
          <a class="settings-nav-item {% if section == 'activity' %}active{% endif %}"
             href="?section=activity"
             data-section="activity"
             data-endpoint="/supervision/partials/activity">
            Activity Log
          </a>
          {% endif %}

          {% if permissions.health %}
          <a class="settings-nav-item ..." href="?section=health" ...>Health</a>
          {% endif %}

          {% if permissions.audit %}
          <a class="settings-nav-item ..." href="?section=audit" ...>Audit Trail</a>
          {% endif %}

        </aside>

        <div class="settings-content">
          <content-container
            initial-endpoint="/supervision/partials/{{ section }}"
          ></content-container>
        </div>

      </div>

      <ramz-dialog id="appDialog"></ramz-dialog>

    </main>
  </div>
</div>

<script>
// nav click handler (مشابه admin_layout)
// + initActivityPage, initHealthPage, initAuditPage
</script>
{% endblock %}
```

### ۱۰.۲. Nav JS pattern

**⚠️ بسیار مهم:** از همان الگوی `admin_layout.html` استفاده کن:
- `nav` click → `history.replaceState` + `ramz:load-content`
- `content-loaded` event → re-init section با `currentListener` anti-dup pattern
- همهٔ `initXxxPage` ها از `getCurrentSection()` چک می‌کنند

### ۱۰.۳. Partials

#### `partials/overview.html`
- Welcome card
- Quick links به Activity, Health, Audit (اگر دسترسی دارند)
- (بدون آمار تکراری از admin_panel)

#### `partials/activity.html`
- Filter bar: User dropdown, Type dropdown, Date range (from/to), Success checkbox, Search button, Reset button
- `<ramz-table id="activityTable">`
- Pagination

#### `partials/health.html`
- Stat cards: DB Size, Active Sessions, Activity (last 24h), Failed Logins (24h)
- Sessions by role (small table یا badge grid)
- Table counts (جدول ۲ ستونه با ~۱۰ ردیف)
- Refresh button

#### `partials/audit.html`
- Filter bar: Admin dropdown, Action dropdown, Entity type, Date range, Search/Reset
- `<ramz-table id="auditTable">`
- Pagination

---

## ۱۱. لایهٔ Service و منطق

### ۱۱.۱. `SupervisionService` (در `services.py`)

```python
class SupervisionService:
    def __init__(self, db_service, template_service, logger=None):
        self.db = db_service
        self.template_service = template_service
        self.logger = logger

    # --- Activity ---
    async def list_activities(self, filters, offset, limit):
        """Return (rows, total)."""
        return await self.db.admin_list_activities(filters, offset, limit)

    async def list_activity_users(self):
        """Return [{user_id, username, full_name}] for filter dropdown."""
        return await self.db.list_users_for_filter()

    async def list_activity_types(self):
        """Return [{type_id, type_name}] from activity_type table."""
        return await self.db.get_activity_types()

    # --- Health ---
    async def get_health_stats(self):
        """Return stats dict — see contract in section 9.3."""
        ...

    # --- Audit ---
    async def list_audit_actions(self, filters, offset, limit):
        """Return (rows, total)."""
        return await self.db.admin_list_audit_logs(filters, offset, limit)

    async def list_audit_admins(self):
        """Return users who have audit entries (distinct admin_id)."""
        ...
```

### ۱۱.۲. `db_manager_service` additions

```python
# Activity (may need new method or extend existing)
async def admin_list_activities(self, filters, offset, limit):
    # filters: {user_id, activity_type, date_from, date_to, success}
    ...

async def admin_count_activities(self, filters):
    ...

async def list_users_for_filter(self):
    """Lightweight: only users with activity entries."""
    ...

# Audit (new in T76.4.1)
async def admin_list_audit_logs(self, filters, offset, limit):
    ...

async def admin_count_audit_logs(self, filters):
    ...

async def admin_list_audit_admins(self):
    """Distinct admin_ids with audit entries."""
    ...
```

### ۱۱.۳. Health stats — محاسبات

```python
async def get_health_stats(self):
    # DB stats
    db_size = os.path.getsize(path_to_sqlite) if db_type == "sqlite" else None
    
    tables = {}
    for t in ["user", "people", "contact", "form", "form_access",
              "role", "user_session", "user_activity_log", "admin_action_log"]:
        tables[t] = await self._db.count_rows(t)
    
    # Sessions
    active_sessions = await self._db.count_active_sessions_total()
    by_role = await self._db.count_active_sessions_by_role()
    
    # Activity
    last_hour = await self._db.count_activity_since(3600)
    last_day = await self._db.count_activity_since(86400)
    last_week = await self._db.count_activity_since(604800)
    
    # Login
    failed_last_hour = await self._db.count_failed_logins_since(3600)
    failed_last_day = await self._db.count_failed_logins_since(86400)
    
    return {...}
```

`count_rows` helper — یک متد عمومی که `SELECT COUNT(*) FROM ?` (با whitelist table names).

---

## ۱۲. سیستم Audit Trail (deep dive)

### ۱۲.۱. مسئولیت‌ها

- **`AdminActionRepository`** — CRUD روی جدول `admin_action_log` (فقط `create` و `list`)
- **`AuditWorkflow`** — wrapper با best-effort logging
- **`AdminPanelService`** — فراخوانی `AuditWorkflow.log()` بعد از هر mutation موفق (یا ناموفق برای ثبت)

### ۱۲.۲. `AuditWorkflow.log()` signature

```python
async def log(
    self,
    admin_id: int,
    action: str,                    # "set_user_role", "toggle_user", ...
    entity_type: str = None,        # "user", "form", "grant", "role"
    entity_id = None,               # int or str
    old_value: dict = None,         # {"role_id": "user"}
    new_value: dict = None,         # {"role_id": "admin"}
    ip: str = None,
    user_agent: str = None,
    success: bool = True,
) -> bool:
    """Best-effort. Never raises. Returns True on success."""
    try:
        await self._db._admin_action_repo.create(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
            ip_address=ip,
            user_agent=user_agent,
            success=success,
        )
        return True
    except Exception as exc:
        if self._logger:
            self._logger.log(
                f"audit log failed: {exc}",
                level="WARNING", tag="audit",
            )
        return False
```

### ۱۲.۳. لیست actionهای audit-شده

همهٔ mutations در `admin_panel` باید audit شوند:

| action | entity_type | old_value | new_value |
|---|---|---|---|
| `set_user_role` | user | `{role_id}` | `{role_id}` |
| `toggle_user` | user | `{enabled}` | `{enabled}` |
| `reset_password` | user | None | None |
| `create_form` | form | None | `{form_id, form_name}` |
| `update_form` | form | `{form_name, description}` | `{...}` |
| `delete_form` | form | `{form_id, form_name}` | None |
| `toggle_form_lock` | form | `{lock}` | `{lock}` |
| `create_grant` | grant | None | `{role_id, form_id, level}` |
| `update_grant_level` | grant | `{level}` | `{level}` |
| `delete_grant` | grant | `{role_id, form_id, level}` | None |
| `create_role` | role | None | `{role_id, role_name, rank}` |
| `update_role` | role | `{name, rank, enabled}` | `{...}` |
| `delete_role` | role | `{role_id, role_name}` | None |
| `toggle_role_lock` | role | `{lock}` | `{lock}` |

### ۱۲.۴. نحوهٔ wiring در `AdminPanelService`

**گزینه‌ها:**

- **Option A** — service متد audit را صدا می‌زند، `ip` و `user_agent` به عنوان kwargs اضافه می‌شوند
- **Option B** — route handler بعد از موفقیت service، audit می‌کند
- **Option C** — یک context object در سراسر درخواست

**انتخاب: Option A** — self-contained، semantic در service layer، route handler فقط `ip` و `ua` را پاس می‌دهد.

```python
# services.py
async def set_user_role(
    self, target_user_id, new_role_id, current_user_id,
    ip=None, user_agent=None,
):
    # ... existing checks ...
    target = await self.db.get_user_by_id(target_user_id)
    old_role = target.role_id
    
    ok, code = await self.db.admin_set_user_role(target_user_id, new_role_id)
    
    if ok:
        await self._audit.log(
            admin_id=current_user_id,
            action="set_user_role",
            entity_type="user", entity_id=target_user_id,
            old_value={"role_id": old_role},
            new_value={"role_id": new_role_id},
            ip=ip, user_agent=user_agent,
        )
    else:
        # Log failed attempt (for debugging + security)
        await self._audit.log(
            admin_id=current_user_id,
            action="set_user_role",
            entity_type="user", entity_id=target_user_id,
            new_value={"role_id": new_role_id, "error": code},
            ip=ip, user_agent=user_agent,
            success=False,
        )
    
    return ok, code
```

Route handler:
```python
ip, ua = _get_client_info(request)   # helper موجود
ok, code = await admin_service.set_user_role(
    target_user_id, new_role_id, user_id,
    ip=ip, user_agent=ua,
)
```

### ۱۲.۵. مقیاس‌پذیری

جدول `admin_action_log` append-only است و می‌تواند بزرگ شود. با ۱۰ admin × ۱۰۰ action/روز = ۱۰۰۰ ردیف/روز = ۳۶۵k/سال. SQLite هنوز OK است، اما در آینده:
- retention policy (حذف بعد از ۹۰ روز)
- archive به جدول سرد
- یا migration به NoSQL (مشابه `user_activity_log`)

**الان اقدام نکن.** فقط در docs ثبت کن که retention policy در آینده لازم است.

---

## ۱۳. ثبت Extension

فقط یک extension در `ui.user_menu.items`:

```python
# در module.py
component_service.register_extension(
    point="ui.user_menu.items",
    data={
        "label": "Supervision",
        "url": "/supervision",
        "icon": "👁️",
        "order": 20,
    },
    form_id="supervision.view",
    module_name="supervision",
)
```

**هیچ extension در `ui.topbar.actions`** — چون "Back to Panel" از `user_panel` می‌آید و "Back to Admin Panel" در `page-head` supervision هست.

---

## ۱۴. نقشهٔ راه فازها

### ۱۴.۱. جدول خلاصه

| Phase | Tasks | Schema | Effort |
|---|---|---|---|
| **1. Foundation** | T76.1.1, T76.1.2 | v10.1 | ~1 روز |
| **2. Activity** | T76.2 | v10.1 | ~0.5 روز |
| **3. Health** | T76.3 | v10.1 | ~0.5 روز |
| **4. Audit** | T76.4.1, T76.4.2 | v11.0 | ~1.5 روز |
| **5. Close** | T76.5 | v11.0 | ~0.5 روز |
| **Total** | 7 tasks | — | ~4 روز |

### ۱۴.۲. ترتیب و وابستگی

```
T76.1.1 (seeds) ───┐
                   ├──▶ T76.1.2 (module) ──▶ T76.2 (activity)
                   │                      ├──▶ T76.3 (health)
                   │                      └──▶ T76.4.1 (audit schema) ──▶ T76.4.2 (audit UI)
                   │                                                              │
                   └──────────────────────────────────────────────────────────────┴──▶ T76.5 (close)
```

**قاعده:** در هر لحظه یک تسک. تسک بعدی فقط بعد از تأیید قبلی.

### ۱۴.۳. قواعد cross-phase

1. **هر تسک یک گزارش مستقل** با فرمت `task-prompt.md`
2. **همهٔ تست‌ها دستی** — هیچ test framework در پروژه نیست
3. **Schema version bump فقط در T76.4.1** — بقیه data-only
4. **مستندات فقط در T76.5** — تا آخر تغییرات قطعی شود

---

## ۱۵. فاز ۱: Foundation

### ۱۵.۱. T76.1.1 — Seeds + create_db.v10.1

**هدف:** دادهٔ supervision آماده شود، بدون تغییر schema.

**خروجی:**

- `db_scripts/seed_supervision.v1.0.sql` (جدید)
- `db_scripts/create_db.v10.1.sql` (جدید — کپی از v10.0 + supervision data)

**گام‌های کلیدی:**

1. seed file با ۷ form + ۱۲ grant (4×3 role)
2. create_db.v10.1 = v10.0 + supervision forms/grants در همان بلوک‌های `INSERT INTO form` و `INSERT INTO form_access`
3. هدر v10.1 + changelog entry

**معیار پذیرش:**

- [ ] `seed_supervision.v1.0.sql` اجرا می‌شود بدون خطا روی DB v10
- [ ] `create_db.v10.1.sql` اجرا می‌شود بدون خطا روی fresh DB
- [ ] `SELECT COUNT(*) FROM form WHERE form_id LIKE 'supervision.%'` = 7
- [ ] `SELECT COUNT(*) FROM form_access WHERE form_id LIKE 'supervision.%'` = 12
- [ ] admin/manager/super-admin همه `supervision.view` دارند
- [ ] system-admin ندارد

**تست دستی:**

```bash
sqlite3 data/rmz_data.db < db_scripts/seed_supervision.v1.0.sql
sqlite3 data/rmz_data.db "SELECT role_id, COUNT(*) FROM form_access WHERE form_id LIKE 'supervision.%' GROUP BY role_id;"
# expected: admin|4, manager|4, super-admin|4
```

### ۱۵.۲. T76.1.2 — Module skeleton

**هدف:** ماژول قابل لود + shell + placeholder sections.

**خروجی:**

- `app/supervision/manifest.json`
- `app/supervision/module.py`
- `app/supervision/routes.py`
- `app/supervision/services.py`
- `app/supervision/templates/supervision_layout.html`
- `app/supervision/templates/partials/{overview,activity,health,audit,coming-soon}.html`
- `app_settings.json` (تغییر — افزودن `supervision` به `app_modules`)

**گام‌های کلیدی:**

1. **manifest.json** — طبق الگوی `admin_panel`
2. **module.py** — `start()`:
   - دریافت `component_service`, `template_service`, `db_service`, `http_api`, `message_service`
   - ثبت `SupervisionService` در `context.services["supervision_service"]`
   - ثبت template directory
   - ثبت components (`brand`, `user-menu`, `card`, `topbar`, `progress-bar`, `content-container`, `dialog`, `table`)
   - ثبت extension `ui.user_menu.items`
   - `register_routes(...)`
3. **routes.py**:
   - `_ensure_authenticated` (کپی از admin_panel)
   - `_render_error_page` (کپی)
   - `GET /supervision` — shell با permissions محاسبه شده
   - `POST /supervision/partials/{section}` — placeholder render
   - `_ensure_section_access(user_id, section)` helper
4. **services.py** — `SupervisionService` خالی، آماده برای T76.2/T76.3/T76.4
5. **supervision_layout.html** — طبق section 10.1
6. **partials/overview.html** — Welcome + quick links (به activity/health/audit اگر دسترسی دارند)
7. **partials/{activity,health,audit}.html** — placeholder با پیام "Coming soon" (کپی از `admin_panel/partials/coming-soon.html`)
8. **app_settings.json** — `supervision` را بعد از `admin_panel` اضافه کن

**معیار پذیرش:**

- [ ] `/supervision` لود می‌شود (اگر کاربر admin/manager/super-admin)
- [ ] Nav سایدبار ۴ آیتم (Overview, Activity, Health, Audit) نمایش داده می‌شود
- [ ] فقط آیتم‌های مجاز (بر اساس permissions)
- [ ] کلیک روی هر آیتم → content-container partial لود می‌کند
- [ ] Overview نشان داده می‌شود (Welcome + quick links)
- [ ] بقیه بخش‌ها placeholder
- [ ] "Supervision" در user menu (وقتی admin/manager/super-admin وارد می‌شود)
- [ ] "Supervision" در user menu visible نیست برای user/limit-user/up-user
- [ ] کاربر بدون `supervision.view` به `/supervision` → 403 error page
- [ ] فعال/غیرفعال کردن `supervision` در `app_settings.json` بدون خطا کار می‌کند

**تست دستی:**

1. login admin → menu → "Supervision" ظاهر → کلیک → page load
2. Nav: ۴ آیتم → کلیک روی هر کدام → partial load
3. logout → login user → menu → "Supervision" **نیست**
4. `supervision` را از `app_settings.json` حذف → restart → `/supervision` → 404 → برگردان

**⚠️ دام رایج:** فراموش کردن `template_service.register_module_assets` — بدون آن، کامپوننت‌ها لود نمی‌شوند و صفحه خالی است.

**⚠️ دام رایج ۲:** فراموش کردن `_has_admin_access` معادل — supervision نیاز به `admin_panel.view` **ندارد**. فقط `supervision.view`.

---

## ۱۶. فاز ۲: Activity Viewer

### ۱۶.۱. T76.2 — Activity Log Viewer

**هدف:** نمایش activity log با فیلتر و pagination.

**خروجی:**

- `partials/activity.html` — بازنویسی کامل (filter bar + ramz-table + pagination)
- `routes.py` — ۳ endpoint جدید
- `services.py` — ۳ متد جدید
- `db_manager_service.py` — ۲-۳ متد جدید (`admin_list_activities` بسط)
- `supervision_layout.html` — `initActivityPage` + `activityState` + `currentListener`

**گام‌های کلیدی:**

1. **`db_manager_service.admin_list_activities(filters, offset, limit)`** — بسط `ActivityRepository` با فیلترهای بیشتر
2. **`services.SupervisionService.list_activities(...)`** — wrapper
3. **routes:**
   - `POST /supervision/activity/list` — JSON (filter + pagination)
   - `POST /supervision/activity/users` — user dropdown options
   - `POST /supervision/activity/types` — type dropdown options
4. **partials/activity.html** — filter bar + ramz-table + pagination
5. **JS:**
   - `activityState = { filters, offset, total, currentListener }`
   - `initActivityPage` — fetch users/types once, bind filters, load
   - `ramz:table-action` listener با `currentListener` (برای row click → navigate به profile)

**معیار پذیرش:**

- [ ] جدول activity با ۵ ستون (User, Type, IP, Result, Time)
- [ ] صفحه‌بندی ۵۰/صفحه
- [ ] فیلتر User dropdown → جدول فیلتر می‌شود
- [ ] فیلتر Type dropdown → جدول فیلتر می‌شود
- [ ] Date range → جدول فیلتر می‌شود
- [ ] Success checkbox → فقط موفق/ناموفق
- [ ] ترکیب فیلترها با AND کار می‌کند
- [ ] Reset → همه چیز به حالت اول
- [ ] Enter روی search → trigger filter
- [ ] کلیک روی ردیف → navigate به `/profile?user_id=X` (اگر داریم) یا console log

**تست دستی:**

1. `/supervision?section=activity` → جدول load
2. User filter = admin → فقط activities admin
3. Type filter = login → فقط login events
4. Date from = today → فقط امروز
5. ترکیب: User=admin + Type=login + Date=today → subset

**⚠️ دام رایج:** `ActivityRepository.get_by_user` **نیاز به بسط دارد**. فعلاً فقط per-user کار می‌کند، نه all-users. این تسک باید `admin_list_activities` جدید اضافه کند (فیلتر روی همهٔ userها).

---

## ۱۷. فاز ۳: Health Dashboard

### ۱۷.۱. T76.3 — System Health

**هدف:** نمایش وضعیت لحظه‌ای سیستم.

**خروجی:**

- `partials/health.html` — بازنویسی کامل (stat cards + tables)
- `routes.py` — ۱ endpoint جدید (`POST /supervision/health/stats`)
- `services.py` — `get_health_stats()`
- `db_manager_service.py` — چند متد کمکی (`count_rows`, `count_active_sessions_by_role`, `count_activity_since`, `count_failed_logins_since`)
- `supervision_layout.html` — `initHealthPage`

**گام‌های کلیدی:**

1. **helpers در db_manager_service:**
   ```python
   async def count_rows(self, table_name: str) -> int:
       # whitelist check!
       allowed = {"user", "people", "contact", "form", "form_access",
                  "role", "user_session", "user_activity_log",
                  "admin_action_log"}
       if table_name not in allowed:
           return 0
       ...
   ```
2. **routes** — `POST /supervision/health/stats` با permission
3. **partials/health.html** — ۴ stat card + session by role + row counts table
4. **JS** — `initHealthPage` — fetch + populate + auto-refresh button

**معیار پذیرش:**

- [ ] ۴ کارت آماری: DB Size, Active Sessions, Activity 24h, Failed Logins 24h
- [ ] جدول "Sessions by role"
- [ ] جدول "Row counts" با ~۹ ردیف
- [ ] Refresh button → fetch مجدد
- [ ] اعداد منطقی (مثلاً user count = عدد واقعی userها)

**تست دستی:**

1. `/supervision?section=health` → load
2. تعداد user = همانی که در admin_panel هست
3. Active sessions → تطابق با login فعلی + other sessions
4. Refresh → اعداد به‌روز

**⚠️ دام رایج:** `db_type` ممکن است PostgreSQL/MySQL باشد در آینده — `os.path.getsize` فقط برای SQLite کار می‌کند. برای `db_size` چک کن:
```python
try:
    db_size = os.path.getsize(db_path)
except (OSError, TypeError):
    db_size = None
```

---

## ۱۸. فاز ۴: Audit Trail

### ۱۸.۱. T76.4.1 — Schema + Repository + Workflow

**هدف:** زیرساخت audit، بدون UI.

**خروجی:**

- `db_scripts/migration_v10_to_v11.sql` (جدید)
- `db_scripts/create_db.v11.0.sql` (جدید)
- `app/db_manager/repositories/admin_action_repository.py` (جدید)
- `app/db_manager/workflows/audit_workflow.py` (جدید)
- `app/db_manager/repositories/__init__.py` (تغییر — export جدید)
- `app/db_manager/workflows/__init__.py` (تغییر — export جدید)
- `app/db_manager/db_manager_service.py` (تغییر — `_admin_action_repo`, `_audit_workflow`, `admin_list_audit_logs`, `admin_count_audit_logs`)

**گام‌های کلیدی:**

1. migration + create_db.v11
2. `AdminActionRepository` با `create()`, `list()`, `count()`, `list_admins()`
3. `AuditWorkflow.log()` — best-effort
4. wire در `DbManagerService.__init__`
5. `DbManagerService.admin_list_audit_logs(filters, offset, limit)` — با JOIN به `user` برای نام admin
6. `DbManagerService.admin_count_audit_logs(filters)`
7. `DbManagerService.admin_list_audit_admins()` — distinct admin_ids

**معیار پذیرش:**

- [ ] migration اجرا می‌شود بدون خطا
- [ ] `SELECT * FROM admin_action_log` = 0 ردیف اولیه
- [ ] `audit_workflow.log(...)` با موفقیت ردیف اضافه می‌کند
- [ ] `admin_list_audit_logs` با filter کار می‌کند
- [ ] create_db.v11.0 اجرا می‌شود بدون خطا

**تست دستی:**

```bash
# migration
sqlite3 data/rmz_data.db < db_scripts/migration_v10_to_v11.sql
sqlite3 data/rmz_data.db "PRAGMA table_info(admin_action_log);"
# expect 10 columns

# create_db fresh
sqlite3 /tmp/test_v11.db < db_scripts/create_db.v11.0.sql
sqlite3 /tmp/test_v11.db "SELECT name FROM sqlite_master WHERE type='table' AND name='admin_action_log';"
```

### ۱۸.۲. T76.4.2 — Wire + Route + UI

**هدف:** audit logging فعال + viewer.

**خروجی:**

- `app/admin_panel/services.py` (تغییر — `_audit` + فراخوانی `log()` در همهٔ mutation methods)
- `app/admin_panel/routes.py` (تغییر — پاس دادن `ip`, `user_agent` به service، افزودن `_get_client_info` helper)
- `app/supervision/routes.py` (تغییر — `POST /supervision/audit/list`, `/audit/admins`)
- `app/supervision/services.py` (تغییر — `list_audit_actions`, `list_audit_admins`)
- `app/supervision/templates/partials/audit.html` (بازنویسی)
- `app/supervision/templates/supervision_layout.html` (تغییر — `initAuditPage`)

**گام‌های کلیدی:**

1. **`AdminPanelService.__init__`** — `self._audit = db_service._audit_workflow`
2. **همهٔ متدهای mutation** — audit بعد از انجام (موفق یا ناموفق) با `old_value`/`new_value`
3. **routes در admin_panel** — `_get_client_info(request)` helper + پاس دادن به service
4. **routes در supervision** — ۲ endpoint جدید
5. **partials/audit.html** — filter bar + ramz-table + pagination
6. **JS** — `initAuditPage` با filters

**معیار پذیرش:**

- [ ] هر mutation در admin_panel یک ردیف در `admin_action_log` ثبت می‌کند
- [ ] ردیف شامل `admin_id`, `action`, `entity_type`, `entity_id`, `old_value`, `new_value`, `ip`, `timestamp` است
- [ ] mutation ناموفق هم ثبت می‌شود با `success=0`
- [ ] `/supervision?section=audit` → جدول نمایش می‌دهد
- [ ] فیلتر Admin → subset
- [ ] فیلتر Action → subset
- [ ] فیلتر Entity type → subset
- [ ] Date range → subset

**تست دستی:**

1. action در admin_panel (مثلاً toggle user) → audit ثبت می‌شود
2. `/supervision?section=audit` → ردیف نمایش داده می‌شود
3. Filter action=set_user_role → فقط role changeها
4. Filter admin=admin → فقط actions همان admin

**⚠️ دام رایج:** audit نباید عملیات را break کند. همیشه `try/except` در `AuditWorkflow.log` و `return False` در خطا. **همچنین** در `AdminPanelService`، خطای audit را نادیده بگیر.

---

## ۱۹. فاز ۵: Polish و Close

### ۱۹.۱. T76.5 — Polish + Docs + Close

**هدف:** بستن Gen 3.

**خروجی:**

- `docs/supervision.md` (جدید — reference کامل)
- `docs/README.md` (تغییر — افزودن supervision به index + Gen 3 milestone)
- `docs/access-control.md` (تغییر — افزودن supervision forms به per-button matrix)
- `docs/admin-panel.md` (تغییر — بند کوتاه: "Audit logging integrates with supervision")
- `initial-review-report.md` → v3.0 (افزودن Supervision + Gen 3 complete)

**معیار پذیرش:**

- [ ] همهٔ فازها end-to-end تست شده‌اند
- [ ] `python -m py_compile` روی همهٔ فایل‌های تغییر یافته
- [ ] `docs/supervision.md` ≥ ۲۰۰ خط، جامع
- [ ] initial-review-report v3.0 آپدیت شده
- [ ] هیچ فایل deprecated در docs باقی نیست

**End-to-end test checklist:**

- [ ] admin login → menu → supervision → ۴ بخش → همه load
- [ ] manager login → همان
- [ ] super-admin login → همان
- [ ] user login → supervision در menu نیست، `/supervision` → 403
- [ ] action در admin_panel → audit در supervision ثبت
- [ ] activity filter کار می‌کند
- [ ] health stats نمایش می‌دهد
- [ ] refresh هر بخش → محتوای به‌روز
- [ ] `supervision` disable در app_settings → همه از کار می‌افتد (بدون خطا)

---

## ۲۰. نگرانی‌های عرضی

### ۲۰.۱. امنیت

| نگرانی | راه‌حل |
|---|---|
| Session hijack | همان `is_session_valid` + `is_user_enabled` |
| CSRF | همان `credentials: 'same-origin'` + FastAPI session cookies |
| SQL injection در `count_rows` | **whitelist table names** — هرگز raw string |
| Sensitive data در audit | `old_value`/`new_value` ممکن است hash باشد — **هرگز password_hash در audit ننویس** |
| Permission bypass | همه endpoints چک `supervision.X.view` |

### ۲۰.۲. عملکرد

- `admin_action_log` می‌تواند بزرگ شود — index مناسب کافی است برای MVP
- Health stats: هر request چند COUNT query — کافی است (SQLite سریع)
- Activity: `user_activity_log` ممکن است بزرگ باشد — pagination + index
- **هیچ cache در supervision** — داده‌ها لحظه‌ای هستند

### ۲۰.۳. i18n readiness

- همهٔ strings در `partials/*.html` هستند (قابل ترجمه در آینده)
- هیچ hardcode در Python (بجز `messages` در routes — قابل استخراج)
- **الان لازم نیست** — فقط در ساختار در نظر بگیر

### ۲۰.۴. Accessibility

- Semantic HTML
- ARIA labels برای icon-only buttons
- Keyboard navigation (tab, enter, escape) — الگو از admin_panel

---

## ۲۱. دام‌های رایج

| # | دام | راه پیشگیری |
|---|---|---|
| ۱ | فراموش کردن `register_module_assets` | چک: `/supervision` → Components → `<ramz-table>` upgraded |
| ۲ | listener duplicate (`Dialog is already open`) | همیشه `xxxState.currentListener` pattern |
| ۳ | nav `active` state desync | `history.replaceState` + `nav.querySelectorAll` |
| ۴ | partial با `<script>` inline (اجرا نمی‌شود) | همه JS در `supervision_layout.html` |
| ۵ | audit log بدون `old_value` | همیشه قبل از mutation، `old_value` از DB بگیر |
| ۶ | audit شکستن mutation | `try/except` در `AuditWorkflow.log` + نادیده گرفتن نتیجه |
| ۷ | `admin_action_log` FK به user حذف‌شده | `ON DELETE SET NULL` در schema |
| ۸ | Activity filter با `user_id` ناموجود | `int()` conversion + try/except |
| ۹ | Date range invalid | Validation در route + `error` response |
| ۱۰ | Permission check duplicate | helper `_ensure_section_access` |
| ۱۱ | Session revoke interceptor 401 | supervision هم از `_ensure_authenticated` استفاده کند |
| ۱۲ | Nav hide/show desync با URL | `section` variable از `?section=` بخوان، validate کن |
| ۱۳ | `supervision` version vs `admin_panel` version | مستقل هستند — bump مستقل |

---

## ۲۲. الزامات مستندسازی

### ۲۲.۱. `docs/supervision.md` (T76.5)

محتوای حداقلی:

1. Overview (چیست، چرا)
2. URL و grants
3. Sections (۴ تا)
4. Route map
5. Audit trail design (schema + workflow + list of audited actions)
6. Health stats contract
7. Activity filter contract
8. Feature matrix (super-admin/admin/manager)
9. Future roadmap (export, purge, alerting)

### ۲۲.۲. `initial-review-report.md` v3.0

افزودن:

- بخش "Gen 3 (Supervision)" در تاریخچه
- بخش "Supervision Module" با feature matrix
- `admin_action_log` در schema section
- Gen 3 complete status
- به‌روزرسانی "Current state"

### ۲۲.۳. `docs/access-control.md`

افزودن:

- supervision forms به per-button table
- Audit trail design note

### ۲۲.۴. `docs/README.md`

افزودن:

- `supervision.md` به index
- Gen 3 milestone

---

## ۲۳. چک‌لیست تحویل

قبل از اعلام Gen 3 کامل:

**Backend:**
- [ ] همهٔ routes کار می‌کنند
- [ ] همهٔ permission checks درست
- [ ] audit log همهٔ mutations را می‌گیرد
- [ ] هیچ `import مستقیم` بین ماژول‌ها
- [ ] `python -m py_compile` پاس

**Frontend:**
- [ ] هیچ `Dialog is already open` در Console
- [ ] همهٔ sections load
- [ ] Filters کار می‌کنند
- [ ] Pagination کار می‌کند
- [ ] Progress bar در topbar animate

**Schema:**
- [ ] `create_db.v11.0.sql` idempotent
- [ ] `migration_v10_to_v11.sql` یک‌بارمصرف
- [ ] همهٔ seedها idempotent

**Docs:**
- [ ] `docs/supervision.md` ≥ ۲۰۰ خط
- [ ] `initial-review-report.md` v3.0
- [ ] `docs/README.md` آپدیت
- [ ] `docs/access-control.md` آپدیت

**Testing:**
- [ ] e2e test همهٔ paths
- [ ] rank enforcement در admin_panel دست‌نخورده
- [ ] session revoke interceptor کار می‌کند
- [ ] disable/enable module در app_settings بدون خطا

---

## ۲۴. معیارهای پذیرش نهایی

Gen 3 کامل است اگر:

1. **کارکردی:** هر سه هدف اصلی (activity, health, audit) قابل استفاده هستند
2. **امنیت:** همهٔ routes با permission check محافظت شده‌اند
3. **مستندات:** `docs/supervision.md` + initial-review-report v3.0 کامل
4. **تست:** همهٔ handoff checklist items pass
5. **قابلیت نگهداری:** کد از الگوهای موجود پیروی می‌کند
6. **مستقل:** فعال/غیرفعال کردن supervision بدون تأثیر روی admin_panel
7. **Data integrity:** `admin_action_log` append-only، هیچ داده‌ای گم نمی‌شود
8. **Compatibility:** schema v11 backward-compatible با v10 (فقط additive)

**آماده برای Gen 4:** (2FA, password reset, email verification, subscription, billing, ...)

---

## پیوست A — نقشهٔ فایل‌های تغییر یافته

| فاز | فایل‌های جدید | فایل‌های تغییر یافته |
|---|---|---|
| T76.1.1 | `seed_supervision.v1.0.sql`, `create_db.v10.1.sql` | — |
| T76.1.2 | `app/supervision/*` (همه), `supervision_layout.html`, `partials/*.html` | `app_settings.json` |
| T76.2 | — | `supervision/routes.py`, `supervision/services.py`, `db_manager_service.py`, `partials/activity.html`, `supervision_layout.html` |
| T76.3 | — | `supervision/routes.py`, `supervision/services.py`, `db_manager_service.py`, `partials/health.html`, `supervision_layout.html` |
| T76.4.1 | `migration_v10_to_v11.sql`, `create_db.v11.0.sql`, `admin_action_repository.py`, `audit_workflow.py` | `repositories/__init__.py`, `workflows/__init__.py`, `db_manager_service.py` |
| T76.4.2 | — | `admin_panel/services.py`, `admin_panel/routes.py`, `supervision/routes.py`, `supervision/services.py`, `partials/audit.html`, `supervision_layout.html` |
| T76.5 | `docs/supervision.md` | `docs/README.md`, `docs/access-control.md`, `docs/admin-panel.md`, `initial-review-report.md` |

---

## پیوست B — قواعد مطلق (یادآوری)

1. ❌ **هرگز Lit, Shadow DOM, JS framework**
2. ❌ **هرگز import مستقیم بین ماژول‌ها** — همه از `context.services`
3. ❌ **هرگز `window.confirm` / `window.alert`** — فقط `appDialog`
4. ❌ **هرگز seed در کد Python** — فقط `db_scripts/*.sql`
5. ❌ **هرگز `condition_of` / `form.enabled` / `required_condition`** — حذف شده
6. ❌ **هرگز `role_name` برای منطق** — فقط `role_id`
7. ✅ **همیشه `_ensure_authenticated` + per-section check**
8. ✅ **همه action حساس → `passwordConfirm`** (در supervision **هیچ** action حساس نیست — read-only)
9. ✅ **همیشه `currentListener` anti-dup pattern**
10. ✅ **همیشه migration یک‌بارمصرف با backup**

---

## پیوست C — تماس با تیم

**مالک پروژه:** [نام]
**مسئول Gen 3:** [نام]
**مدل AI همراه:** Claude / Local AI

**سؤال، ابهام، تصمیم:** قبل از شروع هر تسک، PRE-FLIGHT checklist را با مالک پروژه چک کن.

---

**پایان سند | آماده برای T76.1.1**
