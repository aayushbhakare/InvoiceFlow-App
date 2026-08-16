# InvoiceFlow

An AI-powered invoicing and payment collection platform built specifically for Indian freelancers and SMEs. 

InvoiceFlow streamlines your billing process by automatically calculating taxes, generating professional PDFs, and ensuring you get paid faster with automated WhatsApp reminders and seamless Razorpay integration. It also features a built-in conversational AI assistant to manage your finances effortlessly.

## 🚀 Key Features

- **Smart Invoicing:** Automatic routing of CGST, SGST, and IGST based on client state, plus HSN/SAC code support.
- **AI Accountant:** Built-in conversational AI powered by Google Gemini. Just chat to create invoices, search for clients, or check your revenue.
- **Automated Reminders:** Background cron jobs via Celery automatically scan for overdue invoices and send polite Email & WhatsApp (Twilio) reminders.
- **Seamless Payments:** Integrated Razorpay allows clients to pay instantly via UPI, NEFT, or Cards directly from the invoice link.
- **CA Reporting:** Export your entire billing history to CSV in one click for easy tax filing.
- **100% Mobile Responsive:** Manage your business from your phone, tablet, or desktop.

## 📸 Screenshots

- Screenshots are present in Screeshot folder

## 🛠️ Tech Stack

**Backend**
- Python / Django 
- Django REST Framework (DRF)
- PostgreSQL (Primary Database)
- Redis & Celery (Background tasks & cron jobs)
- SimpleJWT (Authentication)

**Frontend**
- Vanilla HTML, CSS, JavaScript
- Fully custom responsive CSS (No heavy UI frameworks)

**Third-Party Integrations**
- **Google Gemini API:** Natural language AI assistant.
- **Twilio API:** Automated WhatsApp messaging.
- **Razorpay API:** Payment gateway and webhooks.

## 💻 Local Setup & Installation

### Prerequisites
Make sure you have the following installed on your machine:
- Python 3.9+
- PostgreSQL
- Redis Server (Required for Celery)

### Step-by-Step Guide

**1. Clone the repository**
```bash
git clone https://github.com/aayushbhakare/InvoiceFlow_app.git
cd Invoice_app
```

**2. Setup Virtual Environment**
```bash
python -m venv pvenv
source pvenv/bin/activate  # On Windows use `pvenv\Scripts\activate`
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

**4. Environment Variables**
Copy the example environment file and fill in your credentials (you will need API keys for Gemini, Twilio, and Razorpay):
```bash
cp .env.example .env
```

**5. Database Setup**
Ensure PostgreSQL is running and you have created a database matching your `.env` configuration. Then run migrations:
```bash
python manage.py migrate
```

**6. Start the Development Servers**

You will need three terminal windows to run the full stack locally.

**Terminal 1: Django Backend**
```bash
python manage.py runserver
```

**Terminal 2: Celery Worker**
```bash
celery -A backend worker -l info
```

**Terminal 3: Celery Beat (Cron Jobs)**
```bash
celery -A backend beat -l info
```

**7. Frontend Access**
Because the frontend is built with vanilla HTML/JS, you can serve it using a simple live server (like VS Code Live Server) on port 5500.
Access the app at: `http://127.0.0.1:5500/frontend/landingpage.html`

## 🤖 Using the AI Assistant

The AI Assistant is integrated directly into the dashboard. It has access to your database and can perform actions on your behalf. Simply ask it questions like:
- *"Show me all unpaid invoices for Sharma Builders."*
- *"Create a new client named Rahul Deshmukh at rahul@example.com."*
- *"Send a WhatsApp reminder to Mehta Textiles."*

*(Note: Sensitive actions like deleting records or sending messages will always ask for your explicit confirmation before executing).*

## 🧪 Testing

This project uses `pytest` for running automated tests. Make sure your virtual environment is active and dependencies are installed, then run:

```bash
pytest
```

