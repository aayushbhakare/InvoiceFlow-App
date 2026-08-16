# InvoiceFlow — Project Overview

> **A full-stack Invoice Management System with AI assistant, Razorpay payment gateway, automated email/WhatsApp reminders, recurring invoices, and a rich vanilla JS frontend.**

---

## Table of Contents

1. [Project Summary](#1-project-summary)
2. [Tech Stack](#2-tech-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [Directory Structure](#4-directory-structure)
5. [Database Models](#5-database-models)
6. [API Endpoints](#6-api-endpoints)
7. [Business Logic & Serializers](#7-business-logic--serializers)
8. [AI Assistant (InvoiceFlow AI)](#8-ai-assistant-invoiceflow-ai)
9. [Background Tasks (Celery)](#9-background-tasks-celery)
10. [Notification Services](#10-notification-services)
11. [Payment Gateway (Razorpay)](#11-payment-gateway-razorpay)
12. [Frontend Pages](#12-frontend-pages)
13. [Authentication & Security](#13-authentication--security)
14. [Configuration & Environment Variables](#14-configuration--environment-variables)
15. [Testing](#15-testing)
16. [Deployment](#16-deployment)

---

## 1. Project Summary

**InvoiceFlow** is a Django REST Framework (DRF) + vanilla JS SPA-style application that allows freelancers and small businesses to:

- Create and manage invoices with line items, tax, and discount calculations
- Manage clients and reusable services
- Send invoices and reminders via **email** (with PDF attachments) and **WhatsApp** (via Twilio)
- Accept online payments via **Razorpay** (hosted payment page + webhooks)
- Use an AI chat assistant powered by **Google Gemini** to manage everything conversationally
- Generate **recurring invoices** on weekly / monthly / quarterly schedules
- View a rich **dashboard** with analytics (revenue, outstanding, overdue)
- Download invoice **PDFs** (rendered via WeasyPrint)

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | Django 6.0.5 + Django REST Framework 3.17 |
| Database | PostgreSQL (via `psycopg2-binary`) |
| Authentication | JWT — `djangorestframework-simplejwt` |
| Task Queue | Celery 5.6 with Redis as broker & result backend |
| Scheduled Tasks | Celery Beat |
| AI Assistant | Google Gemini (`google-genai 2.10`) via function calling |
| Email | Django SMTP (Gmail) — HTML templates + PDF attachments |
| WhatsApp | Twilio WhatsApp API |
| Payment Gateway | Razorpay (Orders API + Webhooks) |
| PDF Generation | WeasyPrint 68 |
| Cryptography | `cryptography` library (Fernet symmetric encryption for Razorpay secret) |
| CORS | `django-cors-headers` |
| Static Files | WhiteNoise |
| Frontend | Vanilla HTML/CSS/JS (no framework) |
| Testing | pytest + pytest-django + pytest-playwright (E2E) |
| Production Server | Gunicorn |
| Env Management | `django-environ` |

---

## 3. Architecture Overview

```
+-------------------------------------------------------------------+
|                        Frontend (Browser)                         |
|  landingpage -- dashboard -- createinvoice -- createclient        |
|  createservice -- profile -- pay (public) -- ai_chat              |
+--------------------------------+----------------------------------+
                                 | REST API (JWT Bearer tokens)
                                 | CORS from localhost:5500
+--------------------------------v----------------------------------+
|                  Django REST Framework (DRF)                      |
|  ViewSets: Invoice, LineItem, Service, Client, RecurringInvoice   |
|  APIViews: Register, Profile, DeleteAccount                       |
|  Function views: PDF download, AI chat, Razorpay ops              |
+------+--------------------------------------------+--------------+
       | Django ORM                                  | Celery tasks
+------v-----------+                      +----------v-----------+
|   PostgreSQL     |                      |  Redis (broker)      |
|   Database       |                      |  * Celery worker     |
+------------------+                      |  * Celery beat       |
                                          +----------------------+

External Services:
  * Gmail SMTP (email + PDF)
  * Twilio WhatsApp API
  * Razorpay Orders API + Webhook
  * Google Gemini API (AI chat)
```

---

## 4. Directory Structure

```
Invoice_app/
|-- backend/                   # Django project config
|   |-- settings.py            # All settings (DB, Celery, JWT, CORS, logging)
|   |-- urls.py                # Root URL config (admin + api/ routes)
|   |-- celery.py              # Celery app definition
|   |-- asgi.py
|   +-- wsgi.py
|
|-- invoices/                  # Core Django app
|   |-- models.py              # All DB models (10 models)
|   |-- serializers.py         # DRF serializers with business logic
|   |-- views.py               # ViewSets + API views
|   |-- urls.py                # App-level URL routing
|   |-- tasks.py               # Celery tasks (reminders, overdue scan, recurring)
|   |-- ai_agent.py            # Gemini chat loop + pending action handler
|   |-- ai_tools.py            # 19 AI tool definitions (TOOL_REGISTRY)
|   |-- crypto.py              # Fernet encrypt/decrypt for Razorpay secret
|   |-- throttles.py           # Custom login rate throttle
|   |-- admin.py               # Django admin registrations
|   |-- migrations/            # DB migration files
|   |-- services/
|   |   |-- email_service.py   # send_invoice_email(), send_reminder_email()
|   |   |-- pdf_service.py     # generate_invoice_pdf() via WeasyPrint
|   |   +-- whatsapp_service.py # send_whatsapp_reminder() via Twilio
|   +-- templates/
|       +-- invoices/
|           +-- emails/        # HTML email templates
|
|-- frontend/                  # Vanilla JS + HTML + CSS
|   |-- landingpage.html / .js # Login / registration page
|   |-- dashboard.html / .css / .js      # Invoice list + stats dashboard
|   |-- dynamicdashboard.html / .js      # Extended dashboard view
|   |-- createinvoice.html / .css / .js  # Invoice create/edit form
|   |-- createclient.html / .css / .js   # Client create/edit form
|   |-- createservice.html / .css / .js  # Service create/edit form
|   |-- profile.html / .css / .js        # User profile + bank details
|   |-- pay.html / .js                   # Public payment page (Razorpay)
|   |-- ai_chat.css / .js                # AI chat widget
|   |-- utils.js                         # Shared auth helper (getAuthHeaders)
|   +-- favicon.svg
|
|-- manage.py
|-- requirements.txt           # All Python dependencies (pinned)
|-- requirements-test.txt      # Test-only deps
|-- Procfile                   # Gunicorn + Celery worker + Celery beat
|-- pytest.ini                 # Pytest config
|-- test_scenario.py           # Integration / scenario tests
|-- test_negative.py           # Negative / edge-case API tests
|-- test_ui.py                 # Playwright E2E UI tests
|-- .env.example               # Template for all required env vars
+-- .gitignore
```

---

## 5. Database Models

### `Services`
Reusable service catalog per user.

| Field | Type | Notes |
|---|---|---|
| `user` | FK -> User | Scoped per user |
| `name` | CharField(100) | |
| `description` | TextField | Optional |
| `rate` | DecimalField | Default hourly/unit rate |

---

### `Client`
Business clients associated with a user.

| Field | Type | Notes |
|---|---|---|
| `user` | FK -> User | |
| `name` | CharField(255) | |
| `contact_person` | CharField | Optional |
| `email` | EmailField | Used for sending invoices |
| `phone` | CharField | Used for WhatsApp reminders |
| `state`, `city`, `address`, `pincode` | Various | For GST (IGST vs CGST/SGST logic) |
| `is_active` | BooleanField | Inactive clients block new invoices |

---

### `Invoice`
Core invoice record.

| Field | Type | Notes |
|---|---|---|
| `user` | FK -> User | |
| `client` | FK -> Client | `PROTECT` — cannot delete client with invoices |
| `invoice_number` | CharField(25) | Auto-generated: `INV-YYYY-MM-NNNN` (sequential, retry on race condition) |
| `issue_date`, `due_date` | DateField | |
| `total_amount` | DecimalField | Computed and stored |
| `status` | CharField | DRAFT / SENT / PAID / OVERDUE / CANCELLED |
| `discount_percentage` | DecimalField | Applied before tax |
| `tax_rate` | DecimalField | Default 18% GST |
| `client_state` | CharField | Determines IGST vs CGST+SGST split |
| `bank_details`, `notes` | TextField | Appear on PDF |
| `payment_token` | UUIDField | Unique token for public Razorpay payment link |

**Auto-numbering logic**: On `save()`, generates sequential `INV-YYYY-MM-NNNN`. Retries up to 5 times on `IntegrityError` to handle race conditions.

---

### `LineItem`
Individual billable items on an invoice.

| Field | Type | Notes |
|---|---|---|
| `invoice` | FK -> Invoice | CASCADE delete |
| `services` | FK -> Services | `SET_NULL` — keeps line item if service deleted |
| `service_name` | CharField | Snapshot of service name at invoice time |
| `rate` | DecimalField | Snapshot of rate at invoice time |
| `total_hours` | DecimalField | Quantity/hours |

`line_total = rate x total_hours`

---

### `Profile`
Extended user profile with business and bank details.

| Field | Type | Notes |
|---|---|---|
| `user` | OneToOne -> User | |
| `display_name` | CharField | Shown in emails and PDFs |
| `entity_type` | CharField | INDIVIDUAL / COMPANY (auto-detected from GSTIN) |
| `gstin` | CharField | GST number; triggers entity type detection |
| `bank_name`, `account_number`, `ifsc_code`, `upi_id` | Various | Auto-fetches bank name from Razorpay IFSC API |
| `razorpay_key_id` | CharField | Plain |
| `razorpay_key_secret` | CharField | **Encrypted at rest** via Fernet before saving |

**`razorpay_key_secret` encryption**: `save()` encrypts on write; `get_razorpay_key_secret()` decrypts on read.

---

### `NotificationLog`
Audit trail of every email/WhatsApp sent.

| Field | Type | Notes |
|---|---|---|
| `invoice` | FK -> Invoice | |
| `event_type` | CharField | INVOICE_SENT / REMINDER_BEFORE_DUE / REMINDER_ON_DUE / REMINDER_AFTER_DUE / PAYMENT_RECEIVED / STATUS_CHANGED |
| `delivery_status` | CharField | PENDING / SUCCESS / FAILED |
| `recipient_email` | EmailField | Also used for WhatsApp phone |
| `error_message` | TextField | On failure |
| `metadata` | JSONField | Extra context (day_offset, payment_id, channel) |

Indexed on `(invoice, event_type)` and `(invoice, timestamp)`.

---

### `Payment`
Records of payments against invoices.

| Field | Type | Notes |
|---|---|---|
| `invoice` | FK -> Invoice | |
| `amount` | DecimalField | |
| `payment_method` | CharField | UPI / NET_BANKING / NEFT / RAZORPAY |
| `reference_number` | CharField | Manual reference |
| `razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature` | CharField | For Razorpay payments |

When cumulative payments >= `invoice.total_amount`, invoice is auto-marked `PAID`.

---

### `RecurringInvoice`
Template for auto-generating invoices on a schedule.

| Field | Type | Notes |
|---|---|---|
| `user` | FK -> User | |
| `client` | FK -> Client | |
| `frequency` | CharField | WEEKLY / MONTHLY / QUARTERLY |
| `next_issue_date` | DateField | Updated after each generation |
| `end_date` | DateField | Optional stop date |
| `max_occurrences` | IntegerField | Optional count limit |
| `completed_occurrences` | IntegerField | Incremented each run |
| `template_data` | JSONField | Snapshot of items, tax, discount, notes |

---

### `ChatMessage`
Persisted AI chat history per user (last 16 hours).

| Field | Type | Notes |
|---|---|---|
| `user` | FK -> User | |
| `role` | CharField | `user` / `model` |
| `content` | TextField | Message text |
| `tool_calls` | JSONField | Serialized tool call data |

`cleanup_old_messages()` deletes messages older than 16 hours automatically.

---

### `PendingAction`
Holds AI tool calls that require user confirmation before execution.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user` | FK -> User | |
| `tool_name` | CharField | Name of the tool to execute |
| `tool_args` | JSONField | Arguments to pass |
| `status` | CharField | pending / approved / rejected / expired |
| `expires_at` | DateTimeField | 10-minute timeout |

---

### `AIAuditLog`
Full audit trail of every AI tool execution.

| Field | Type | Notes |
|---|---|---|
| `user` | FK -> User | |
| `tool_name` | CharField | |
| `tool_args` | JSONField | |
| `required_confirmation` | BooleanField | |
| `status` | CharField | success / failed |
| `result` | JSONField | Tool return value |
| `duration_ms` | IntegerField | Execution time |

---

## 6. API Endpoints

### Root URL Config (`backend/urls.py`)

| Method | Path | Description |
|---|---|---|
| `ANY` | `/admin/` | Django admin |
| `ANY` | `/api/` | All app endpoints |
| `POST` | `/api/token/` | JWT login (rate-limited: 5/min) |
| `POST` | `/api/token/refresh/` | JWT refresh (rate-limited: 5/min) |

---

### App URL Config (`invoices/urls.py`)

#### Auth / User

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/register/` | Public | Register new user (email + password) |
| `GET/PATCH` | `/api/profile/` | JWT | Get/update user profile |
| `POST` | `/api/delete-account/` | JWT | Delete account (requires password confirmation) |

#### Invoices (ViewSet — full CRUD)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/invoices/` | JWT | List user's invoices (ordered by `-issue_date`) |
| `POST` | `/api/invoices/` | JWT | Create invoice |
| `GET` | `/api/invoices/{id}/` | JWT | Retrieve invoice |
| `PUT/PATCH` | `/api/invoices/{id}/` | JWT | Update invoice (blocked if PAID) |
| `DELETE` | `/api/invoices/{id}/` | JWT | Delete invoice |
| `POST` | `/api/invoices/{id}/send/` | JWT | Send invoice via email + WhatsApp |
| `GET` | `/api/invoices/{id}/timeline/` | JWT | Notification log for invoice |
| `GET/POST` | `/api/invoices/{id}/payments/` | JWT | List or record payments |
| `GET` | `/api/invoices/{id}/download/` | JWT | Download PDF |

#### Clients, Services, Line Items (ViewSets)

| Path | Description |
|---|---|
| `/api/clients/` | CRUD for clients (scoped to user) |
| `/api/services/` | CRUD for services (scoped to user) |
| `/api/line-items/` | CRUD for line items (scoped via invoice->user) |
| `/api/recurring-invoices/` | CRUD for recurring invoice templates |

#### Payments (Razorpay)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/invoices/{payment_token}/create-order/` | Public | Create Razorpay order |
| `POST` | `/api/invoices/{payment_token}/verify-payment/` | Public | Verify & record Razorpay payment |
| `POST` | `/api/webhooks/razorpay/` | Public (HMAC) | Razorpay webhook handler |

#### AI Chat

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/chat/` | JWT | Send message to AI agent |

Body: `{ "message": "...", "pending_action_id": "..." (optional) }`

---

## 7. Business Logic & Serializers

### Tax Calculation (`InvoiceSerializer`)

GST logic is determined by comparing the **seller's state** (from `Profile.state`) with the **client's state** (`Invoice.client_state`):

- **Same state** -> CGST + SGST (each = `tax_rate / 2`)
- **Different state** -> IGST (= `tax_rate`)

```
subtotal      = Sum(rate x hours) per line item
discount      = subtotal x discount_percentage / 100
taxable       = subtotal - discount
CGST / SGST   = taxable x (tax_rate / 200)   [if intra-state]
IGST          = taxable x (tax_rate / 100)    [if inter-state]
total_amount  = taxable + CGST + SGST + IGST
balance_due   = total_amount - amount_paid
```

### Invoice Locking
- `PAID` invoices cannot be modified (enforced in `InvoiceSerializer.validate()`).
- Inactive clients block invoice creation/modification.

### Payment Auto-Close
When `PaymentSerializer.create()` is called and cumulative payments >= `total_amount`, the invoice status is set to `PAID` automatically and a `PAYMENT_RECEIVED` notification log is created.

### Profile: IFSC Lookup
When saving a profile, if `ifsc_code` is provided but `bank_name` is empty, the serializer hits `https://ifsc.razorpay.com/{ifsc}` to auto-fetch the bank name.

### Profile: Entity Type from GSTIN
The 6th character of the GSTIN determines entity type:
- `P` -> Individual/Proprietor
- `C` -> Company
- `F` -> Partnership Firm
- `H` -> HUF
- `T` -> Trust

### Phone Normalization
`normalize_phone_number()` normalizes 10-digit Indian numbers to `+91XXXXXXXXXX` format for both client and profile phone fields.

---

## 8. AI Assistant (InvoiceFlow AI)

### Architecture (`ai_agent.py`)

The AI agent is a **Gemini function-calling loop** powered by `gemini-3.5-flash`:

```
User message -> ChatMessage saved -> Build history from DB
  -> Create Gemini chat with system prompt + tools
    -> Loop (max 8 turns):
        if response has function_call:
          if requires_confirmation: -> create PendingAction -> return to user
          else: execute tool -> log to AIAuditLog -> feed result back
        else: break
  -> Save AI text response to ChatMessage -> return to frontend
```

**Confirmation flow**: Destructive tools (e.g., `delete_invoice`) create a `PendingAction` with a 10-minute expiry. The frontend shows a confirm button. On approval, the client sends `pending_action_id` which triggers `_handle_pending_action()`.

### AI Tools (`ai_tools.py`) — 19 Tools

All tools are registered via the `@tool()` decorator into `TOOL_REGISTRY`.

| Tool Name | Description | Requires Confirmation |
|---|---|---|
| `create_invoice` | Creates a new draft invoice with line items | No |
| `add_service` | Adds a reusable service to the catalog | No |
| `create_client` | Adds a new client | No |
| `delete_invoice` | Deletes an invoice by number | **Yes** |
| `generate_pdf` | Generates a downloadable PDF for an invoice | No |
| `send_invoice` | Sends invoice email + WhatsApp to client | No |
| `send_reminder` | Sends payment reminder email + WhatsApp | No |
| `record_payment` | Records a manual payment against an invoice | No |
| `get_analytics` | Returns revenue, outstanding, overdue, slowest-paying clients | No |
| `search_invoices` | Searches invoices by client, status, date range | No |
| `search_clients` | Searches clients by name/email | No |
| `search_services` | Searches the service catalog | No |
| `update_client` | Updates client fields | No |
| `update_invoice` | Updates invoice fields (discount, tax, notes, status, due date) | No |
| `update_service` | Updates service name/rate | No |
| `bulk_send_invoices` | Sends all DRAFT invoices (optionally filtered by client) | **Yes** |
| `bulk_send_reminders` | Sends reminders to all SENT/OVERDUE invoices | **Yes** |
| `bulk_record_payments` | Records payments for multiple invoices | **Yes** |
| `bulk_generate_pdfs` | Generates PDFs for a set of invoices | No |

---

## 9. Background Tasks (Celery)

Celery workers are driven by Redis. Three periodic tasks run via **Celery Beat**:

| Task | Cron Schedule | Description |
|---|---|---|
| `scan_upcoming_reminders` | Daily at 09:00 UTC | Scans SENT/OVERDUE invoices for reminder triggers at -3d, 0d, +3d, +7d relative to due date. Sends email + WhatsApp. Skips duplicates via `NotificationLog` check. |
| `scan_overdue_invoices` | Daily at 09:30 UTC | Finds SENT invoices past due date, marks them OVERDUE, logs STATUS_CHANGED. |
| `generate_recurring_invoices` | Daily at 08:00 UTC | Generates invoices from active `RecurringInvoice` templates. Advances `next_issue_date`. Deactivates templates that hit `end_date` or `max_occurrences`. |

**Retry policy**: `send_invoice_email_task` retries up to 3 times with a 5-minute delay on failure.

---

## 10. Notification Services

### Email (`services/email_service.py`)

- **`send_invoice_email(invoice)`**: Renders `invoices/emails/invoice_sent.html`, attaches generated PDF, sends via Django SMTP (Gmail).
- **`send_reminder_email(invoice, reminder_type, metadata)`**: Renders `invoices/emails/reminder.html`, attaches PDF. Subject prefixed with "Overdue: " for `REMINDER_AFTER_DUE`.
- Both functions log to `NotificationLog` on success or failure.
- `from_email` is formatted as `"{display_name} via InvoiceFlow <{smtp_email}>"`.
- Email includes a **payment link**: `{PAYMENT_BASE_URL}/frontend/pay.html?token={payment_token}`

### WhatsApp (`services/whatsapp_service.py`)

- Uses **Twilio WhatsApp sandbox** (`TWILIO_WHATSAPP_NUMBER`).
- Sends contextual messages based on `event_type`:
  - `REMINDER_BEFORE_DUE`: Friendly upcoming reminder
  - `REMINDER_ON_DUE`: Due today notice
  - `REMINDER_AFTER_DUE`: Urgent overdue notice
- Auto-normalizes phone to `+91XXXXXXXXXX` if no country code.
- Logs to `NotificationLog` with `metadata.channel = 'whatsapp'`.

### PDF (`services/pdf_service.py`)

- Uses **WeasyPrint** to render an HTML template to PDF bytes.
- Called by both email services and the download endpoint.

---

## 11. Payment Gateway (Razorpay)

### Flow

```
Client opens pay.html?token={payment_token}
  -> GET /api/invoices/{token}/create-order/    (public)
      -> Creates Razorpay Order (amount in paise)
      -> Returns: order_id, amount, currency, razorpay_key_id
  -> Razorpay JS SDK handles payment UI
  -> POST /api/invoices/{token}/verify-payment/ (public)
      -> HMAC signature verification (SHA-256)
      -> Creates Payment record
      -> Marks invoice PAID
      -> Creates PAYMENT_RECEIVED NotificationLog
```

### Webhook (`/api/webhooks/razorpay/`)

- Handles `payment.captured` events as a fallback.
- Verifies `X-Razorpay-Signature` header with `RAZORPAY_WEBHOOK_SECRET`.
- Idempotent — skips if invoice already PAID.

### Security

- Razorpay Key Secret is **encrypted at rest** in the database using Fernet symmetric encryption (`invoices/crypto.py`).
- Payment page uses `payment_token` (UUID) — not the invoice ID — preventing enumeration.

---

## 12. Frontend Pages

All frontend files are in `/frontend/`. The backend serves `landingpage.html` via Django template rendering at `/`.

| File | Description |
|---|---|
| `landingpage.html/js` | Login and registration. Stores JWT tokens in `localStorage`. |
| `dashboard.html/css/js` | Main invoice list with search, filter by status, send action, delete, PDF download. Shows summary stats (total billed, outstanding, overdue, paid). |
| `dynamicdashboard.html/js` | Extended dashboard with charts and more detailed analytics. |
| `createinvoice.html/css/js` | Invoice create/edit form. Dynamic line item rows. Live total calculation. Client autocomplete. |
| `createclient.html/css/js` | Client create/edit form with validation. |
| `createservice.html/css/js` | Service create/edit form. |
| `profile.html/css/js` | User profile management. Bank details, GSTIN, Razorpay keys, display name. |
| `pay.html/js` | **Public** Razorpay payment page. No auth required. Loaded via `?token=` UUID. |
| `ai_chat.css/js` | Floating AI chat widget used across pages. Handles confirmation flow. |
| `utils.js` | Shared `getAuthHeaders()` helper that reads JWT from `localStorage`. |

### Auth Flow
1. User logs in on `landingpage.html` -> JWT access + refresh tokens saved to `localStorage`.
2. All API calls use `Authorization: Bearer {access_token}`.
3. On 401, frontend attempts token refresh via `/api/token/refresh/`.
4. On failed refresh, user redirected to landing page.

---

## 13. Authentication & Security

### JWT Configuration (`settings.py`)

| Setting | Value |
|---|---|
| Access token lifetime | 30 minutes |
| Refresh token lifetime | 8 hours |
| Rotate refresh tokens | False |
| Blacklist after rotation | True |
| Auth header | `Bearer` |

### Rate Limiting

| Throttle | Rate |
|---|---|
| Anonymous | 100/minute |
| Authenticated user | 1000/minute |
| Login endpoint | 5/minute (custom `LoginRateThrottle`) |

### Production Security Headers (when `DEBUG=False`)

- `SECURE_SSL_REDIRECT = True`
- `SECURE_HSTS_SECONDS = 31536000` (1 year) with subdomains + preload
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_PROXY_SSL_HEADER` set for reverse-proxy (e.g., Heroku)

### Data Security

- Razorpay API secret encrypted at rest using **Fernet** (symmetric AES-128-CBC + HMAC).
- Invoices are user-scoped — queries always filter by `user=request.user`.
- Payment page uses an opaque UUID `payment_token` instead of the invoice PK.

---

## 14. Configuration & Environment Variables

Copy `.env.example` to `.env` and fill in values:

```env
# Django
SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500

# PostgreSQL
DB_NAME=invoiceflow_db
DB_USER=postgres
DB_PASSWORD=...
DB_HOST=localhost
DB_PORT=5432

# Redis (Celery)
REDIS_URL=redis://localhost:6379/0

# Email (Gmail SMTP)
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password   # Gmail app password

# Google Gemini AI
GEMINI_API_KEY=...

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=+14155238886    # Twilio sandbox number

# Razorpay
RAZORPAY_WEBHOOK_SECRET=...
```

> **Note**: `razorpay_key_id` and `razorpay_key_secret` are stored **per user** in the `Profile` model, not in `.env`. Each user configures their own Razorpay account in their profile settings.

---

## 15. Testing

### Test Files

| File | Type | Description |
|---|---|---|
| `test_scenario.py` | Integration | Happy-path scenario tests (register -> create -> send -> pay) |
| `test_negative.py` | Negative | Edge cases, validation errors, unauthorized access, business rule violations |
| `test_ui.py` | E2E (Playwright) | Browser-level UI tests |
| `invoices/test_api.py` | Unit | Basic API unit tests |

### Running Tests

```bash
# All tests
pytest

# Only scenario tests
pytest test_scenario.py -v

# Only negative tests
pytest test_negative.py -v

# UI tests (requires Playwright browsers installed)
pytest test_ui.py -v
```

Config in `pytest.ini`:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = backend.settings
```

---

## 16. Deployment

### Procfile (Heroku-compatible)

```
web:    gunicorn backend.wsgi --bind 0.0.0.0:$PORT
worker: celery -A backend worker -l info
beat:   celery -A backend beat -l info
```

Three processes must run simultaneously:
1. **web** — handles HTTP requests
2. **worker** — processes async tasks (email sending, etc.)
3. **beat** — fires scheduled tasks (reminders, recurring invoices)

### Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env with your credentials

# 3. Apply migrations
python manage.py migrate

# 4. Run Django dev server
python manage.py runserver

# 5. In separate terminals:
celery -A backend worker -l info
celery -A backend beat -l info

# 6. Serve frontend (e.g., VS Code Live Server on port 5500)
# Open frontend/landingpage.html via Live Server
```

---

## Key Design Decisions

1. **Vanilla JS Frontend**: No framework overhead. Each page is a standalone HTML file communicating with the DRF API via `fetch()`.
2. **Payment token UUID**: Clients access the payment page via a UUID token, not the invoice ID, preventing enumeration attacks.
3. **Razorpay secret encrypted at DB level**: Uses Fernet (not just hashing) because the secret must be decrypted to use it — it's a symmetric key stored securely.
4. **AI confirmation gate**: Destructive or bulk write operations go through a `PendingAction` record requiring explicit user approval, preventing accidental data loss via chat.
5. **Tax split logic in serializer**: CGST/SGST vs. IGST is determined at serialization time by comparing seller state (profile) and buyer state (client), not stored pre-calculated.
6. **NotificationLog deduplication**: `scan_upcoming_reminders` checks `NotificationLog` before resending, preventing duplicate reminders even if the task runs multiple times.
7. **Invoice number race-condition handling**: The `save()` method retries up to 5 times on `IntegrityError` for the auto-generated invoice number.
