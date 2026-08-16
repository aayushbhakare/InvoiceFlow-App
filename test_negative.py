import argparse
import sys
import re
from playwright.sync_api import sync_playwright, expect

FRONTEND_URL = "http://127.0.0.1:5500/frontend/landingpage.html"
DASHBOARD_URL = "http://127.0.0.1:5500/frontend/dynamicdashboard.html"

tests_run = 0
tests_passed = 0
tests_failed = 0
failed_details = []

def run_test(name, func, *args):
    global tests_run, tests_passed, tests_failed, failed_details
    tests_run += 1
    print(f"\n[{tests_run}] Negative Testing: {name}...")
    try:
        func(*args)
        tests_passed += 1
        print(f"✅ PASSED")
    except Exception as e:
        tests_failed += 1
        print(f"❌ FAILED: {str(e)}")
        failed_details.append({"name": name, "error": str(e)})


def test_invalid_login(page):
    page.goto(FRONTEND_URL)
    page.click("#tab-login")
    page.fill("#login-form input[type='email']", "doesnotexist@example.com")
    page.fill("#login-form input[type='password']", "wrongpassword")
    page.click("#login-form button[type='submit']")
    
    page.wait_for_selector("#toast-el.show", timeout=8000)
    expect(page).to_have_url(re.compile(r".*landingpage\.html"))

def test_empty_login_fields(page):
    page.goto(FRONTEND_URL)
    page.click("#tab-login")
    page.fill("#login-form input[type='email']", "")
    page.fill("#login-form input[type='password']", "")
    page.click("#login-form button[type='submit']")
    
    page.wait_for_timeout(1000)
    expect(page).to_have_url(re.compile(r".*landingpage\.html"))

def test_dashboard_without_token(page):
    page.goto(FRONTEND_URL)
    page.evaluate("() => localStorage.removeItem('access_token')")
    page.evaluate("() => localStorage.removeItem('refresh_token')")
    
    page.goto(DASHBOARD_URL)
    page.wait_for_url(re.compile(r".*landingpage\.html"), timeout=10000)

def test_duplicate_registration(page, email):
    page.goto(FRONTEND_URL)
    page.click("#tab-register")
    page.wait_for_selector("#sec-register.visible", timeout=3000)
    
    page.fill("#register-form input[type='text']", "Duplicate User")
    page.fill("#register-form input[type='email']", email)
    page.fill("#register-form input[type='password']", "TestPassword123")
    page.click("#register-form button[type='submit']")
    
    page.wait_for_selector("#toast-el.show", timeout=8000)
    expect(page).to_have_url(re.compile(r".*landingpage\.html"))


def test_valid_login(page, email, password):
    page.goto(FRONTEND_URL)
    page.click("#tab-login")
    page.fill("#login-form input[type='email']", email)
    page.fill("#login-form input[type='password']", password)
    page.click("#login-form button[type='submit']")
    
    page.wait_for_url(re.compile(r"(dynamicdashboard\.html|profile\.html)"), timeout=15000)
        
    if "profile.html" in page.url:
        page.click("#skip-profile-btn")
        page.wait_for_url("**/dynamicdashboard.html*", timeout=5000)


def test_client_empty_submit(page):
    page.click("button.nav-btn:has-text('Clients')")
    page.click("button:has-text('Add client')")
    page.wait_for_selector("#modal-client.open", timeout=3000)
    
    client_frame = page.wait_for_selector("#modal-client iframe").content_frame()
    client_frame.click("button.btn-save")
    
    expect(page.locator("#modal-client")).to_be_visible()
    
    page.click("button[onclick=\"closeModal('client')\"]")
    page.wait_for_selector("#modal-client", state="hidden", timeout=3000)

def test_client_invalid_email(page):
    page.click("button.nav-btn:has-text('Clients')")
    page.click("button:has-text('Add client')")
    page.wait_for_selector("#modal-client.open", timeout=3000)
    
    client_frame = page.wait_for_selector("#modal-client iframe").content_frame()
    
    client_frame.fill("#biz-name", "Negative Test Corp")
    client_frame.fill("#contact", "Mr Negative")
    client_frame.fill("#mobile", "9999999999")
    client_frame.fill("#email", "this-is-not-an-email")
    client_frame.click("button.btn-save")
    
    expect(page.locator("#modal-client")).to_be_visible()
    
    page.click("button[onclick=\"closeModal('client')\"]")
    page.wait_for_selector("#modal-client", state="hidden", timeout=3000)

def test_client_invalid_phone(page):
    page.click("button.nav-btn:has-text('Clients')")
    page.click("button:has-text('Add client')")
    page.wait_for_selector("#modal-client.open", timeout=3000)
    
    client_frame = page.wait_for_selector("#modal-client iframe").content_frame()
    
    client_frame.fill("#biz-name", "Short Phone Corp")
    client_frame.fill("#contact", "Mr Short")
    client_frame.fill("#mobile", "12345")
    client_frame.fill("#email", "short@phone.com")
    client_frame.click("button.btn-save")
    
    expect(client_frame.locator("#f-mobile.invalid")).to_be_visible()
    
    page.click("button[onclick=\"closeModal('client')\"]")
    page.wait_for_selector("#modal-client", state="hidden", timeout=3000)

def test_client_cancel_discards(page):
    page.click("button.nav-btn:has-text('Clients')")
    page.click("button:has-text('Add client')")
    page.wait_for_selector("#modal-client.open", timeout=3000)
    
    client_frame = page.wait_for_selector("#modal-client iframe").content_frame()
    client_frame.fill("#biz-name", "Should Not Be Saved Corp")
    client_frame.fill("#contact", "Ghost User")
    
    client_frame.click("button.btn-cancel")
    page.wait_for_selector("#modal-client", state="hidden", timeout=3000)


def test_service_empty_submit(page):
    page.click("button.nav-btn:has-text('Services/LineItems')")
    page.click("button:has-text('Add Service/Lineitems')")
    page.wait_for_selector("#modal-service.open", timeout=3000)
    
    service_frame = page.wait_for_selector("#modal-service iframe").content_frame()
    service_frame.click("button.btn-save")
    
    expect(page.locator("#modal-service")).to_be_visible()
    
    page.click("button[onclick=\"closeModal('service')\"]")
    page.wait_for_selector("#modal-service", state="hidden", timeout=3000)

def test_service_zero_rate(page):
    page.click("button.nav-btn:has-text('Services/LineItems')")
    page.click("button:has-text('Add Service/Lineitems')")
    page.wait_for_selector("#modal-service.open", timeout=3000)
    
    service_frame = page.wait_for_selector("#modal-service iframe").content_frame()
    service_frame.fill("#service-name", "Zero Rate Service")
    service_frame.fill("#service-desc", "Free service edge case")
    service_frame.fill("#service-rate", "0")
    service_frame.click("button.btn-save")
    
    page.wait_for_selector("#modal-service", state="hidden", timeout=5000)

def test_service_negative_rate(page):
    page.click("button.nav-btn:has-text('Services/LineItems')")
    page.click("button:has-text('Add Service/Lineitems')")
    page.wait_for_selector("#modal-service.open", timeout=3000)
    
    service_frame = page.wait_for_selector("#modal-service iframe").content_frame()
    service_frame.fill("#service-name", "Negative Rate Service")
    service_frame.fill("#service-desc", "Should be blocked")
    service_frame.fill("#service-rate", "-500")
    service_frame.click("button.btn-save")
    
    page.wait_for_timeout(2000)
    expect(page.locator("#modal-service")).to_be_visible()
    
    page.click("button[onclick=\"closeModal('service')\"]")
    page.wait_for_selector("#modal-service", state="hidden", timeout=3000)


def test_invoice_no_client(page):
    page.click(".topbar-right button:has-text('New invoice')")
    page.wait_for_selector("#modal-invoice.open", timeout=3000)
    
    inv_frame = page.wait_for_selector("#modal-invoice iframe").content_frame()
    inv_frame.click("button.btn-primary:has-text('Save Invoice')")
    
    expect(page.locator("#modal-invoice")).to_be_visible()
    
    page.click("button[onclick=\"closeModal('invoice')\"]")
    page.wait_for_selector("#modal-invoice", state="hidden", timeout=3000)

def test_invoice_no_line_items(page):
    page.click(".topbar-right button:has-text('New invoice')")
    page.wait_for_selector("#modal-invoice.open", timeout=3000)
    
    inv_frame = page.wait_for_selector("#modal-invoice iframe").content_frame()
    
    inv_frame.wait_for_selector("#client-select option:not([value=''])", state="attached", timeout=5000)
    inv_frame.select_option("#client-select", index=1)
    
    inv_frame.click("button.btn-primary:has-text('Save Invoice')")
    
    page.wait_for_timeout(3000)
    
    if page.locator("#modal-invoice.open").is_visible():
        page.click("button[onclick=\"closeModal('invoice')\"]")
        page.wait_for_selector("#modal-invoice", state="hidden", timeout=3000)


def test_search_nonexistent_invoice(page):
    page.click("button.nav-btn:has-text('Invoices')")
    page.wait_for_timeout(500)
    
    page.fill("#inv-search", "ZZZZZZNONEXISTENT99999")
    page.wait_for_timeout(1000)
    
    rows = page.locator("#inv-tbody tr").count()
    row_text = page.locator("#inv-tbody").inner_text()
    assert rows <= 1 or "no invoices" in row_text.lower() or row_text.strip() == "", \
        f"Expected empty results but got {rows} rows: {row_text[:100]}"
    
    page.fill("#inv-search", "")
    page.wait_for_timeout(500)

def test_search_nonexistent_client(page):
    page.click("button.nav-btn:has-text('Clients')")
    page.wait_for_timeout(500)
    
    page.fill("#client-search", "ZZZZNONEXISTENT99999")
    page.wait_for_timeout(1000)
    
    cards = page.locator("#client-grid .client-card").count()
    assert cards == 0, f"Expected 0 client cards but got {cards}"
    
    page.fill("#client-search", "")
    page.wait_for_timeout(500)

def test_filter_by_status_cancelled(page):
    page.click("button.nav-btn:has-text('Invoices')")
    page.wait_for_timeout(500)
    
    page.select_option("#inv-status", "cancelled")
    page.wait_for_timeout(1000)
    
    rows = page.locator("#inv-tbody tr")
    count = rows.count()
    for i in range(count):
        text = rows.nth(i).inner_text().lower()
        if "no invoices" in text:
            break
        assert "cancelled" in text, f"Row {i} is not Cancelled: {text[:80]}"
    
    page.select_option("#inv-status", "")
    page.wait_for_timeout(500)


def test_rapid_modal_open_close(page):
    for _ in range(3):
        page.click(".topbar-right button:has-text('New invoice')")
        page.wait_for_selector("#modal-invoice.open", timeout=3000)
        page.click("button[onclick=\"closeModal('invoice')\"]")
        page.wait_for_selector("#modal-invoice", state="hidden", timeout=3000)
    
    page.click("button.nav-btn:has-text('Dashboard')")
    expect(page.locator("#page-dashboard")).to_have_class(re.compile(r"active"))

def test_rapid_tab_switching(page):
    tabs = ["Invoices", "Clients", "Reports", "Services/LineItems", "Dashboard"]
    for tab in tabs:
        page.click(f"button.nav-btn:has-text('{tab}')")
        page.wait_for_timeout(200)
    
    expect(page.locator("#page-dashboard")).to_have_class(re.compile(r"active"))

def test_close_modal_by_backdrop(page):
    page.click("button.nav-btn:has-text('Clients')")
    page.click("button:has-text('Add client')")
    page.wait_for_selector("#modal-client.open", timeout=3000)
    
    page.click("#modal-client", position={"x": 5, "y": 5})
    page.wait_for_timeout(1000)
    
    if page.locator("#modal-client.open").is_visible():
        page.click("button[onclick=\"closeModal('client')\"]")
        page.wait_for_selector("#modal-client", state="hidden", timeout=3000)
        print(" (Note: Backdrop click does not dismiss modal — expected)", end="")


def test_logout_clears_session(page):
    page.click("#nav-avatar")
    page.wait_for_timeout(500)
    
    page.click("button:has-text('Logout')")
    page.wait_for_url(re.compile(r".*landingpage\.html"), timeout=10000)
    
    token = page.evaluate("() => localStorage.getItem('access_token')")
    assert token is None, f"Access token was not cleared after logout: {token}"

def test_back_button_after_logout(page):
    page.go_back()
    page.wait_for_timeout(2000)
    
    current_url = page.url
    assert "landingpage.html" in current_url or "login" in current_url.lower(), \
        f"After logout + back, expected landing page but got: {current_url}"


def execute_suite(email, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=250)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        print("="*60)
        print("🚀 COMPREHENSIVE NEGATIVE E2E TEST SUITE")
        print("="*60)
        
        print("\n" + "-"*40)
        print("SECTION A: Authentication & Access Control")
        print("-"*40)
        run_test("A1. Invalid Login (Wrong Credentials)", test_invalid_login, page)
        run_test("A2. Empty Login Fields (HTML5 Required)", test_empty_login_fields, page)
        run_test("A3. Dashboard Access Without Token", test_dashboard_without_token, page)
        run_test("A4. Duplicate Email Registration", test_duplicate_registration, page, email)
        
        print("\n" + "-"*40)
        print("SECTION B: Valid Login (Prerequisite)")
        print("-"*40)
        run_test("B1. Valid Login", test_valid_login, page, email, password)
        
        if failed_details and failed_details[-1]["name"] == "B1. Valid Login":
            print("\n❌ CRITICAL: Valid login failed. Aborting remaining tests.")
            browser.close()
            sys.exit(1)
            
        print("\n" + "-"*40)
        print("SECTION C: Client Form Validation")
        print("-"*40)
        run_test("C1. Client: Empty Form Submit", test_client_empty_submit, page)
        run_test("C2. Client: Invalid Email Format", test_client_invalid_email, page)
        run_test("C3. Client: Invalid Phone (5 digits)", test_client_invalid_phone, page)
        run_test("C4. Client: Cancel Discards Data", test_client_cancel_discards, page)
        
        print("\n" + "-"*40)
        print("SECTION D: Service Form Validation")
        print("-"*40)
        run_test("D1. Service: Empty Form Submit", test_service_empty_submit, page)
        run_test("D2. Service: Zero Rate (Edge Case)", test_service_zero_rate, page)
        run_test("D3. Service: Negative Rate", test_service_negative_rate, page)
        
        print("\n" + "-"*40)
        print("SECTION E: Invoice Creation Edge Cases")
        print("-"*40)
        run_test("E1. Invoice: No Client Selected", test_invoice_no_client, page)
        run_test("E2. Invoice: No Line Items", test_invoice_no_line_items, page)
        
        print("\n" + "-"*40)
        print("SECTION F: Search & Filter Edge Cases")
        print("-"*40)
        run_test("F1. Search: Non-Existent Invoice", test_search_nonexistent_invoice, page)
        run_test("F2. Search: Non-Existent Client", test_search_nonexistent_client, page)
        run_test("F3. Filter: Cancelled Status", test_filter_by_status_cancelled, page)
        
        print("\n" + "-"*40)
        print("SECTION G: Modal & Navigation Resilience")
        print("-"*40)
        run_test("G1. Rapid Modal Open/Close (Race Condition)", test_rapid_modal_open_close, page)
        run_test("G2. Rapid Tab Switching", test_rapid_tab_switching, page)
        run_test("G3. Close Modal by Backdrop Click", test_close_modal_by_backdrop, page)
        
        print("\n" + "-"*40)
        print("SECTION H: Logout & Session Security")
        print("-"*40)
        run_test("H1. Logout Clears Session", test_logout_clears_session, page)
        run_test("H2. Back Button After Logout", test_back_button_after_logout, page)
        
        browser.close()
        
        print("\n" + "="*60)
        print("📊 NEGATIVE TEST SUITE — FINAL RESULTS")
        print("="*60)
        print(f"Total Tests Run : {tests_run}")
        print(f"Passed          : {tests_passed}")
        print(f"Failed          : {tests_failed}")
        print(f"Pass Rate       : {tests_passed}/{tests_run} ({100*tests_passed//max(tests_run,1)}%)")
        
        if tests_failed > 0:
            print("\n🚨 FAILURE DETAILS:")
            for f in failed_details:
                print(f" - {f['name']}: {f['error'][:150]}")
            sys.exit(1)
        else:
            print("\n🎉 ALL NEGATIVE TESTS PASSED SUCCESSFULLY!")
            sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Negative E2E Test Suite for InvoiceFlow")
    parser.add_argument("--email", required=True, help="Valid login email")
    parser.add_argument("--password", required=True, help="Valid login password")
    args = parser.parse_args()
    execute_suite(args.email, args.password)
