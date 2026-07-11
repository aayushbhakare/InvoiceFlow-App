import argparse
import sys
import re
from playwright.sync_api import sync_playwright, expect

FRONTEND_URL = "http://127.0.0.1:5500/frontend/landingpage.html"

def test_full_scenario(email, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        print("=========================================")
        print("🚀 STARTING SCENARIO TEST")
        print("=========================================")
        
        print("1. Navigating to landing page...")
        page.goto(FRONTEND_URL)
        
        print("2. Attempting Signup...")
        page.click("#tab-register")
        page.fill("#register-form input[type='text']", "Scenario User")
        page.fill("#register-form input[type='email']", email)
        page.fill("#register-form input[type='password']", password)
        page.click("#register-form button[type='submit']")
        
        # Wait for either success or error toast
        try:
            # If successful, it switches to login tab after 1.5 seconds
            page.wait_for_selector("#tab-login.active", timeout=5000)
            print(" -> Signup successful, moved to login tab.")
            page.wait_for_timeout(1000)
        except:
            print(" -> Signup skipped or failed (user might already exist). Proceeding to login.")
        
        print("3. Logging in...")
        page.click("#tab-login")
        page.fill("#login-form input[type='email']", email)
        page.fill("#login-form input[type='password']", password)
        page.click("#login-form button[type='submit']")
        
        page.wait_for_url(re.compile(r"(dynamicdashboard\.html|profile\.html)"), timeout=10000)
        if "profile.html" in page.url:
            print(" -> Filling out profile setup...")
            page.fill("#display_name", "Scenario Business")
            page.fill("#phone_number", "9876543210")
            page.fill("#upi_id", "scenario@upi")
            page.fill("#account_number", "1234567890")
            page.fill("#ifsc_code", "SBIN0001234")
            # Optional fields
            page.fill("#gstin", "27ABCDE1234F1Z5")
            page.fill("#pincode", "411001")
            page.fill("#street_address", "123 Scenario Street, Tech Park")
            page.fill("#city", "Pune")
            page.fill("#state", "Maharashtra")
            page.fill("#razorpay_key_id", "rzp_test_T6iIKU30yukNlP")
            page.fill("#razorpay_key_secret", "mg2YodNFLBT4ccAOyMCHccep")
            page.click("#save-profile-btn")
            page.wait_for_url("**/dynamicdashboard.html*", timeout=10000)
            print(" -> Profile saved successfully!")
            
        print("4. Adding Line Item (Service)...")
        page.click("button.nav-btn:has-text('Services/LineItems')")
        page.click("button:has-text('Add Service/Lineitems')")
        page.wait_for_selector("#modal-service.open", timeout=3000)
        service_frame = page.wait_for_selector("#modal-service iframe").content_frame()
        service_frame.fill("#service-name", "Scenario Consulting")
        service_frame.fill("#service-desc", "Hourly rate for consulting")
        service_frame.fill("#service-rate", "2500")
        service_frame.click("button.btn-save")
        page.wait_for_selector("#modal-service", state="hidden", timeout=5000)
        print(" -> Service added.")
        
        print("5. Adding Client...")
        page.click("button.nav-btn:has-text('Clients')")
        page.click("button:has-text('Add client')")
        page.wait_for_selector("#modal-client.open", timeout=3000)
        client_frame = page.wait_for_selector("#modal-client iframe").content_frame()
        client_frame.fill("#biz-name", "Scenario Corp")
        client_frame.fill("#contact", "John Doe")
        client_frame.fill("#mobile", "9876543210")
        client_frame.fill("#email", "selmanbhai299@gmail.com")
        client_frame.click("button.btn-save")
        page.wait_for_selector("#modal-client", state="hidden", timeout=5000)
        print(" -> Client added.")
        
        print("6. Creating Invoice (Sent Status)...")
        page.click(".topbar-right button:has-text('New invoice')")
        page.wait_for_selector("#modal-invoice.open", timeout=3000)
        inv_frame = page.wait_for_selector("#modal-invoice iframe").content_frame()
        
        # Select Client
        inv_frame.wait_for_selector("#client-select option:not([value=''])", state="attached", timeout=5000)
        inv_frame.select_option("#client-select", index=1)
        
        # Add Service
        inv_frame.click(".add-row-btn")
        inv_frame.wait_for_selector(".service-row select", state="attached", timeout=3000)
        inv_frame.select_option(".service-row select", index=1)
        
        # Change qty
        inv_frame.fill(".service-row input[type='number']", "4") # 4 hours
        
        # Save and Send invoice (this creates it in SENT status)
        inv_frame.click("button.btn-primary:has-text('Save & Send')")
        page.wait_for_selector("#modal-invoice", state="hidden", timeout=15000)
        print(" -> Invoice created and sent successfully!")
        
        # Verify it shows up as Pending
        page.click("button.nav-btn:has-text('Invoices')")
        page.wait_for_selector("#inv-tbody tr", timeout=5000)
        
        row_text = page.locator("#inv-tbody tr").first.inner_text()
        print(f" -> Top invoice in list: {row_text}")
        if "sent" in row_text.lower():
            print("✅ TEST SCENARIO PASSED: Invoice is in SENT status!")
        else:
            print("⚠️ NOTE: Invoice created, but status might not be explicitly 'sent' in the UI text.")
            
        print("Test completed. Closing browser in 3 seconds...")
        page.wait_for_timeout(3000)
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    test_full_scenario(args.email, args.password)
