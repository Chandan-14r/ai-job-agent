from playwright.sync_api import sync_playwright
import sys

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[PAGE ERROR] {err}"))

        response = page.goto("http://127.0.0.1:5000", wait_until="networkidle")
        print(f"Page loaded: HTTP {response.status}")

        print("--- Console Logs on Initial Load ---")
        for l in console_logs:
            print("  ", l)

        buttons = page.query_selector_all("button")
        print(f"\nTotal buttons found on page: {len(buttons)}")

        # Test View Mode Switch Buttons
        print("\n--- Testing View Mode Buttons ---")
        btn_table = page.query_selector("#btn-view-table")
        if btn_table:
            btn_table.click()
            page.wait_for_timeout(300)
            table_visible = page.is_visible("#table-view-container")
            cards_hidden = not page.is_visible("#cards-view-container")
            print(f"Table mode clicked: table_visible={table_visible}, cards_hidden={cards_hidden}")

        btn_cards = page.query_selector("#btn-view-cards")
        if btn_cards:
            btn_cards.click()
            page.wait_for_timeout(300)
            cards_visible = page.is_visible("#cards-view-container")
            table_hidden = not page.is_visible("#table-view-container")
            print(f"Cards mode clicked: cards_visible={cards_visible}, table_hidden={table_hidden}")

        # Test Score Filter Buttons
        print("\n--- Testing Score Filter Buttons ---")
        score_85 = page.query_selector("button:text('≥85')")
        if score_85:
            score_85.click()
            page.wait_for_timeout(300)
            visible_cards = page.query_selector_all(".job-item:not([style*='display: none'])")
            print(f"Score >=85 clicked: visible jobs count = {len(visible_cards)}")

        score_all = page.query_selector("button:text('All'):right-of(button:text('≥75'))")
        if score_all:
            score_all.click()
            page.wait_for_timeout(300)
            visible_cards = page.query_selector_all(".job-item:not([style*='display: none'])")
            print(f"Score All clicked: visible jobs count = {len(visible_cards)}")

        # Test Profile Modal Button
        print("\n--- Testing Profile Modal Button ---")
        btn_profile = page.query_selector("button:has-text('Edit Preferences & Contact')")
        if btn_profile:
            btn_profile.click()
            page.wait_for_timeout(500)
            profile_modal_visible = page.is_visible("#profileModal")
            print(f"Profile modal opened: {profile_modal_visible}")
            btn_cancel = page.query_selector("#profileModal button:has-text('Cancel')")
            if btn_cancel:
                btn_cancel.click()
                page.wait_for_timeout(500)
                print(f"Profile modal closed: {not page.is_visible('#profileModal')}")

        # Test Inspect Rubric Button
        print("\n--- Testing Inspect Rubric Modal Button ---")
        inspect_btn = page.query_selector(".job-item button[title='Inspect 100-pt rubric breakdown']")
        if inspect_btn:
            inspect_btn.click()
            page.wait_for_timeout(600)
            job_modal_visible = page.is_visible("#jobModal")
            modal_score = page.inner_text("#modal-score")
            print(f"Job Rubric modal opened: {job_modal_visible}, Score displayed: {modal_score}")
            btn_close_job = page.query_selector("#jobModal button:has-text('Close')")
            if btn_close_job:
                btn_close_job.click()
                page.wait_for_timeout(500)
                print(f"Job modal closed: {not page.is_visible('#jobModal')}")

        # Test Re-verify Link Button
        print("\n--- Testing Verify Link Button ---")
        verify_btn = page.query_selector(".job-item button[title='Test live link accessibility']")
        if verify_btn:
            verify_btn.click()
            page.wait_for_timeout(2000)
            alert_text = page.inner_text("#live-alert-text")
            print(f"Verify link clicked. Alert displayed: '{alert_text}'")

        # Test Telegram Ping Button
        print("\n--- Testing Telegram Ping Button ---")
        page.on("dialog", lambda dialog: (print(f"Dialog shown: {dialog.message}"), dialog.accept()))
        btn_telegram = page.query_selector("button:has-text('Ping Telegram Bot')")
        if btn_telegram:
            btn_telegram.click()
            page.wait_for_timeout(1000)

        # Test Emergency Stop Button
        print("\n--- Testing Emergency Stop Button ---")
        btn_emergency = page.query_selector("#btn-emergency")
        if btn_emergency:
            btn_emergency.click()
            page.wait_for_timeout(1000)

        print("\n--- Console Errors During Testing ---")
        errors = [l for l in console_logs if "[error]" in l or "[PAGE ERROR]" in l]
        for e in errors:
            print("  ", e)
        if not errors:
            print("  None! No console errors encountered.")

        browser.close()

if __name__ == "__main__":
    main()
