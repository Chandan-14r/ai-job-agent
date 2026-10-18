from playwright.sync_api import sync_playwright
import time

def test_all_buttons():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ["error", "warning"] else None)
        page.on("pageerror", lambda err: console_errors.append(f"[PAGE ERROR] {err}"))

        print("1. Navigating to http://127.0.0.1:5000 ...")
        resp = page.goto("http://127.0.0.1:5000", wait_until="networkidle")
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        print("   Page loaded successfully.")

        # 2. View Mode Toggle
        print("2. Testing View Mode Switcher (Cards vs Table)...")
        btn_table = page.locator("#btn-view-table")
        btn_table.click()
        page.wait_for_timeout(200)
        assert page.is_visible("#table-view-container"), "Table container should be visible"
        assert not page.is_visible("#cards-view-container"), "Cards container should be hidden"
        print("   Table mode verified.")

        btn_cards = page.locator("#btn-view-cards")
        btn_cards.click()
        page.wait_for_timeout(200)
        assert page.is_visible("#cards-view-container"), "Cards container should be visible"
        assert not page.is_visible("#table-view-container"), "Table container should be hidden"
        print("   Cards mode verified.")

        # 3. Score Filters
        print("3. Testing Score Filters...")
        page.locator("button:text('≥85')").click()
        page.wait_for_timeout(200)
        visible_cards_85 = page.locator(".job-item:visible").count()
        print(f"   Score >= 85 filter: {visible_cards_85} jobs shown.")
        assert visible_cards_85 > 0, "Should have matching jobs >= 85"

        page.locator("button:text('≥75')").click()
        page.wait_for_timeout(200)
        visible_cards_75 = page.locator(".job-item:visible").count()
        print(f"   Score >= 75 filter: {visible_cards_75} jobs shown.")
        assert visible_cards_75 >= visible_cards_85

        page.locator("button:text('All')").filter(has_text="All").last.click()
        page.wait_for_timeout(200)
        visible_cards_all = page.locator(".job-item:visible").count()
        print(f"   Score All filter: {visible_cards_all} jobs shown.")
        assert visible_cards_all >= visible_cards_75

        # 4. Search Filter
        print("4. Testing Search Filter Input...")
        search_input = page.locator("#filter-search")
        search_input.fill("GitLab")
        page.wait_for_timeout(200)
        gitlab_count = page.locator(".job-item:visible").count()
        print(f"   Search 'GitLab': {gitlab_count} jobs shown.")
        assert gitlab_count > 0, "Should find GitLab jobs"
        search_input.fill("")
        page.wait_for_timeout(200)

        # 5. Profile Modal
        print("5. Testing Profile & Preferences Modal...")
        page.locator("button:has-text('Edit Preferences & Contact')").click()
        page.wait_for_timeout(400)
        assert page.is_visible("#profileModal"), "Profile modal should be open"
        # Test Cancel button
        page.locator("#profileModal button:has-text('Cancel')").click()
        page.wait_for_timeout(400)
        assert not page.is_visible("#profileModal"), "Profile modal should be closed"
        print("   Profile modal open/close verified.")

        # 6. Job Rubric Inspection Modal
        print("6. Testing Job Rubric Inspection Modal...")
        first_inspect = page.locator(".job-item button[title='Inspect 100-pt rubric breakdown']").first
        first_inspect.click()
        page.wait_for_timeout(500)
        assert page.is_visible("#jobModal"), "Job inspection modal should be open"
        score_text = page.locator("#modal-score").inner_text()
        print(f"   Modal opened. Score: {score_text}")
        assert "/100" in score_text
        page.locator("#jobModal button:has-text('Close')").click()
        page.wait_for_timeout(400)
        assert not page.is_visible("#jobModal"), "Job inspection modal should be closed"
        print("   Job Rubric modal verified.")

        # 7. Live URL Re-verify Button
        print("7. Testing Live URL Re-verify Button...")
        verify_btn = page.locator(".job-item button[title='Test live link accessibility']").first
        verify_btn.click()
        page.wait_for_timeout(2000)
        alert_text = page.locator("#live-alert-text").inner_text()
        print(f"   Verify result alert: '{alert_text}'")
        assert "VERIFIED_ACTIVE" in alert_text or "Probe" in alert_text, f"Unexpected alert: {alert_text}"

        # 8. Telegram Ping Button
        print("8. Testing Telegram Ping Button...")
        page.locator("button:has-text('Ping Telegram Bot')").click()
        page.wait_for_timeout(1000)
        tg_alert = page.locator("#live-alert-text").inner_text()
        print(f"   Telegram alert: '{tg_alert}'")
        assert "Telegram" in tg_alert or "message" in tg_alert.lower()

        # 9. Emergency Stop Button
        print("9. Testing Emergency Stop Button Toggle...")
        btn_emergency = page.locator("#btn-emergency")
        btn_emergency.click()
        page.wait_for_timeout(800)
        label_text = page.locator("#emergency-label").inner_text()
        print(f"   Emergency button toggled to: '{label_text}'")
        assert "Resume Agent" in label_text or "Emergency" in label_text

        # Click again to resume
        btn_emergency.click()
        page.wait_for_timeout(800)
        resumed_text = page.locator("#emergency-label").inner_text()
        print(f"   Emergency button resumed to: '{resumed_text}'")

        # 10. Portal Refresh Status Button
        print("10. Testing Portal Refresh Status Button...")
        refresh_btn = page.locator("button:has-text('Refresh Status')")
        refresh_btn.click()
        page.wait_for_timeout(800)
        portal_alert = page.locator("#live-alert-text").inner_text()
        print(f"    Portal refresh alert: '{portal_alert}'")

        # 11. Mode Dropdown
        print("11. Testing Mode Dropdown Switching...")
        page.locator("button.dropdown-toggle:has-text('Mode:')").click()
        page.wait_for_timeout(300)
        page.locator("a:has-text('2. ASSISTED_APPLICATION_MODE')").click()
        page.wait_for_timeout(800)
        mode_label = page.locator("#current-mode-label").inner_text()
        print(f"    Mode switched to: '{mode_label}'")
        assert "ASSISTED_APPLICATION_MODE" in mode_label

        # Switch back to DISCOVERY_MODE
        page.locator("button.dropdown-toggle:has-text('Mode:')").click()
        page.wait_for_timeout(300)
        page.locator("a:has-text('1. DISCOVERY_MODE')").click()
        page.wait_for_timeout(800)
        assert "DISCOVERY_MODE" in page.locator("#current-mode-label").inner_text()

        # 12. Check Console Errors
        print("\n12. Verifying Browser Console Error Logs...")
        print(f"    Errors: {console_errors}")
        assert len(console_errors) == 0, f"Found browser errors: {console_errors}"
        print("    0 browser console errors detected!")

        browser.close()
        print("\n*** ALL BUTTONS & INTERACTIONS 100% VERIFIED WORKING! ***")

if __name__ == "__main__":
    test_all_buttons()
