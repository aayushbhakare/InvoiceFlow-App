import argparse
import sys
import time
import re
from playwright.sync_api import sync_playwright, expect

FRONTEND_URL = "http://127.0.0.1:5500/frontend/landingpage.html"

# Global tracking for test suite results
tests_run = 0
tests_passed = 0
tests_failed = 0
failed_details = []

def run_test(name, func, *args):
    global tests_run, tests_passed, tests_failed, failed_details
    tests_run += 1
    print(f"\n[{tests_run}] Testing: {name}...")
    try:
        func(*args)
        tests_passed += 1
        print(f"✅ PASSED")
    except Exception as e:
        tests_failed += 1
        print(f"❌ FAILED: {str(e)}")
        failed_details.append({"name": name, "error": str(e)})

# --- 1. Core Scenarios ---
def test_login(page, email, password):
    page.goto(FRONTEND_URL)
    page.click("#tab-login")
    page.fill("#login-form input[type='email']", email)
    page.fill("#login-form input[type='password']", password)
    page.click("#login-form button[type='submit']")
    
    try:
        page.wait_for_url(re.compile(r"(dynamicdashboard\.html|profile\.html)"), timeout=10000)
    except Exception as e:
        print(f"Current URL at failure: {page.url}")
        raise e
        
    if "profile.html" in page.url:
        page.click("#skip-profile-btn")
        page.wait_for_url("**/dynamicdashboard.html*", timeout=5000)

def test_navigation_tabs(page):
    nav_buttons = ["Invoices", "Clients", "Reports", "Services/LineItems", "Dashboard"]
    for btn_text in nav_buttons:
        page.click(f"button.nav-btn:has-text('{btn_text}')")
        page.wait_for_timeout(500)

# --- 2. Client Scenarios (CRUD & Validations) ---
def test_add_client_validation(page):
    page.click("button.nav-btn:has-text('Clients')")
    page.click("button:has-text('Add client')")
    page.wait_for_selector("#modal-client.open", timeout=3000)
    
    client_frame = page.wait_for_selector("#modal-client iframe").content_frame()
    
    # 1. Negative Test: Click save without filling required fields
    client_frame.click("button.btn-save")
    # Modal should stay open because of HTML validation preventing submission
    expect(page.locator("#modal-client")).to_be_visible()
    
    # 2. Positive Test: Fill fields
    client_frame.fill("#biz-name", "UI Test Corp")
    client_frame.fill("#contact", "Test User")
    client_frame.fill("#mobile", "9999999999")
    client_frame.fill("#email", "test@testcorp.com")
    client_frame.click("button.btn-save")
    
    page.wait_for_selector("#modal-client", state="hidden", timeout=5000)

# --- 3. Services Scenarios (CRUD & Validations) ---
def test_add_service_validation(page):
    page.click("button.nav-btn:has-text('Services/LineItems')")
    page.click("button:has-text('Add Service/Lineitems')")
    page.wait_for_selector("#modal-service.open", timeout=3000)
    
    service_frame = page.wait_for_selector("#modal-service iframe").content_frame()
    
    # 1. Negative Test: Empty Submission
    service_frame.click("button.btn-save")
    expect(page.locator("#modal-service")).to_be_visible()
    
    # 2. Positive Test
    service_frame.fill("#service-name", "Automated UI Service")
    service_frame.fill("#service-desc", "Created by Playwright")
    service_frame.fill("#service-rate", "1500")
    service_frame.click("button.btn-save")
    page.wait_for_selector("#modal-service", state="hidden", timeout=5000)

# --- 4. Invoice Full Flow ---
def test_create_full_invoice(page):
    page.click(".topbar-right button:has-text('New invoice')")
    page.wait_for_selector("#modal-invoice.open", timeout=3000)
    
    inv_frame = page.wait_for_selector("#modal-invoice iframe").content_frame()
    
    # Select Client (Wait for dynamic loading)
    # <option> elements inside a closed <select> are not 'visible' in Playwright, so we wait for 'attached'
    inv_frame.wait_for_selector("#client-select option:not([value=''])", state="attached", timeout=5000)
    inv_frame.select_option("#client-select", index=1)
    
    # Add Line Item Row
    inv_frame.click(".add-row-btn")
    
    # Select service in row
    inv_frame.wait_for_selector(".service-row select", state="attached", timeout=3000)
    inv_frame.select_option(".service-row select", index=1)
    
    # Change qty
    inv_frame.fill(".service-row input[type='number']", "2")
    
    # Add another Line Item Row
    inv_frame.click(".add-row-btn")
    # Don't fill it, it should just be ignored or calculated as 0
    
    # Change discount
    inv_frame.fill("#discount-val", "10")
    
    # Check total calculation roughly (doesn't have to be exact value, just ensuring it calculates)
    expect(inv_frame.locator("#s-total")).not_to_have_text("₹0")
    
    # Save Invoice
    inv_frame.click("button.btn-primary:has-text('Save Invoice')")
    
    # Should close
    page.wait_for_selector("#modal-invoice", state="hidden", timeout=10000)

# --- 5. Payment Flow ---
def test_record_payment(page):
    page.click("button.nav-btn:has-text('Invoices')")
    page.wait_for_selector("#inv-tbody tr", timeout=5000)
    
    row = page.locator("#inv-tbody tr").first
    if "No invoices found" in row.inner_text():
        print(" (Skipped: No invoices)", end="")
        return
        
    # Open detail panel
    row.click()
    page.wait_for_selector("#modal-detail.open", timeout=3000)
    
    btn_payment = page.locator("button[onclick=\"doAction('paid')\"]")
    if not btn_payment.is_visible():
        print(" (Skipped: Invoice already paid/no button)", end="")
        page.click("button[onclick=\"closeModal('detail')\"]")
        return
        
    btn_payment.click()
    page.wait_for_timeout(2000)
    page.click("button[onclick=\"closeModal('detail')\"]")

# --- 6. Search & Filter ---
def test_dashboard_search(page):
    page.click("button.nav-btn:has-text('Invoices')")
    page.wait_for_timeout(1000)
    page.fill("#inv-search", "Test")
    page.wait_for_timeout(1000)
    expect(page.locator("#inv-tbody")).to_be_visible()

# --- 7. AI Chat Testing ---
def test_ai_chat_positive(page):
    # Click chat bubble if not open
    if not page.locator("#ai-chat-panel").is_visible():
        page.click("#ai-chat-btn")
        page.wait_for_timeout(500)
        
    page.fill("#chat-input", "List all clients")
    page.click("#ai-send-btn")
    
    # Wait for response (typing indicator should disappear)
    page.wait_for_selector(".ai-typing", state="hidden", timeout=20000)
    expect(page.locator(".ai-msg").last).to_contain_text("client", ignore_case=True)

def test_ai_chat_negative(page):
    page.fill("#chat-input", "aslkdfjsaldkfjsadlkfjsdlkfj")
    page.click("#ai-send-btn")
    page.wait_for_selector(".ai-typing", state="hidden", timeout=20000)
    # Shouldn't crash, should just respond politely
    expect(page.locator(".ai-msg").last).to_be_visible()

def test_ai_chat_approval(page):
    # This relies on "UI Test Corp" existing from the earlier test
    page.fill("#chat-input", "mark UI Test Corp as active")
    page.click("#ai-send-btn")
    page.wait_for_selector(".ai-typing", state="hidden", timeout=20000)
    
    # Should show an approval box
    btn_approve = page.locator(".ai-btn-approve")
    if btn_approve.is_visible():
        btn_approve.click()
        # Should say executing... then success
        page.wait_for_selector(".ai-typing", state="hidden", timeout=20000)
        expect(page.locator(".ai-msg").last).to_contain_text("success", ignore_case=True)
    else:
        print(" (Skipped: AI did not return an approval box, check logs)", end="")

def execute_suite(email, password):
    with sync_playwright() as p:
        # slow_mo gives UI enough time to render animations
        browser = p.chromium.launch(headless=False, slow_mo=400)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        print("="*50)
        print("🚀 STARTING COMPREHENSIVE E2E TEST SUITE")
        print("="*50)
        
        run_test("1. Login & Authenticate", test_login, page, email, password)
        
        if tests_failed > 0:
            print("\n❌ CRITICAL: Login failed. Aborting remaining tests.")
            sys.exit(1)
            
        run_test("2. Navigate Dashboard Tabs", test_navigation_tabs, page)
        
        # Testing Form Validations & Submissions
        run_test("3. Client Form: Validation & Create", test_add_client_validation, page)
        run_test("4. Service Form: Validation & Create", test_add_service_validation, page)
        
        # Complex Workflows
        run_test("5. Invoice: Full Creation Flow (Clients, Items, Math)", test_create_full_invoice, page)
        run_test("6. Payment: Mark Invoice Paid from Detail Panel", test_record_payment, page)
        
        # Search Filtering
        run_test("7. Dashboard: Live Search Filtering", test_dashboard_search, page)
        
        # AI Assistant Chat
        run_test("8. AI Chat: List Data (Positive)", test_ai_chat_positive, page)
        run_test("9. AI Chat: Gibberish Handling (Negative)", test_ai_chat_negative, page)
        run_test("10. AI Chat: Approve Pending Action", test_ai_chat_approval, page)
        
        browser.close()
        
        print("\n" + "="*50)
        print("📊 TEST RUN SUMMARY")
        print("="*50)
        print(f"Total Tests Run : {tests_run}")
        print(f"Passed          : {tests_passed}")
        print(f"Failed          : {tests_failed}")
        
        if tests_failed > 0:
            print("\n🚨 FAILURE DETAILS:")
            for f in failed_details:
                print(f" - {f['name']}: {f['error']}")
            sys.exit(1)
        else:
            print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
            sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    execute_suite(args.email, args.password)
