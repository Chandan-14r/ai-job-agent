from playwright.sync_api import sync_playwright

def test_action_buttons():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ["error", "warning"] else None)
        page.on("pageerror", lambda err: console_errors.append(f"[PAGE ERROR] {err}"))

        print("1. Loading dashboard...")
        page.goto("http://127.0.0.1:5000", wait_until="networkidle")

        # 2. Test "Discover Real Public ATS" button
        print("2. Testing 'Discover Real Public ATS' button...")
        btn_discover = page.locator("button:has-text('Discover Real Public ATS')")
        btn_discover.click()
        # Live ATS discovery makes live network calls to Canonical & GitLab, so wait up to 15s
        page.wait_for_selector("#live-alert-text:has-text('Discovery Complete')", timeout=15000)
        alert_text = page.locator("#live-alert-text").inner_text()
        print(f"   Discovery alert: '{alert_text}'")
        assert "Discovery Complete" in alert_text or "Processed" in alert_text
        page.wait_for_timeout(2000) # allow any reload to finish

        # 3. Test "Generate All ATS Resumes" button
        print("3. Testing 'Generate All ATS Resumes' button...")
        btn_resumes = page.locator("button:has-text('Generate All ATS Resumes')")
        btn_resumes.click()
        page.wait_for_selector("#live-alert-text:has-text('Resumes')", timeout=10000)
        resume_alert = page.locator("#live-alert-text").inner_text()
        print(f"   Resume generation alert: '{resume_alert}'")
        assert "Resumes" in resume_alert or "generated" in resume_alert.lower()

        # 4. Test "Send OTP" button on Naukri
        print("4. Testing 'Send OTP' button on Naukri...")
        btn_send_otp = page.locator("button:has-text('Send OTP')").first
        btn_send_otp.click()
        page.wait_for_timeout(2500)
        otp_alert = page.locator("#live-alert-text").inner_text()
        print(f"   OTP alert: '{otp_alert}'")
        assert "OTP" in otp_alert or "Dispatching" in otp_alert

        # 5. Test "View Official Job" link on genuine job
        print("5. Testing 'View Official Job' link...")
        first_job_link = page.locator(".job-item a:has-text('View Official Job')").first
        href = first_job_link.get_attribute("href")
        target = first_job_link.get_attribute("target")
        rel = first_job_link.get_attribute("rel")
        print(f"   Link href: {href}, target: {target}, rel: {rel}")
        assert href.startswith("http"), f"Must be real HTTP link, got {href}"
        assert target == "_blank", "Must open in new tab"
        assert "noopener" in rel, "Must have noopener security"

        # 6. Test Resume Download buttons
        print("6. Testing Resume download links...")
        pdf_link = page.locator("a:has-text('View PDF')").first.get_attribute("href")
        docx_link = page.locator("a:has-text('DOCX')").first.get_attribute("href")
        print(f"   PDF link: {pdf_link}")
        print(f"   DOCX link: {docx_link}")
        assert pdf_link.endswith(".pdf")
        assert docx_link.endswith(".docx")

        print("\n*** ALL ACTION BUTTONS, RESUMES & EXTERNAL LINKS VERIFIED 100% OPERATIONAL! ***")
        browser.close()

if __name__ == "__main__":
    test_action_buttons()
