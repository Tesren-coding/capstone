"""Smoke tests for JSON-path diagnostics and usable New Line after draft failures."""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB


def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1450, 'height': 950})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.evaluate("""() => {
            sessionStorage.setItem('capstone-builder-draft',JSON.stringify({scenario:{invalid:true}}));
            const originalFetch = window.fetch;
            window.fetch = (url, options) => {
                if (url === '/import-scenario')
                    return Promise.resolve(new Response(JSON.stringify({error:'Old draft is invalid'}),
                        {status:400,headers:{'Content-Type':'application/json'}}));
                if (url === '/scenario-storage-status')
                    return Promise.resolve(new Response(JSON.stringify({backend:'json',count:0,
                        directory:'C:\\\\old-project\\\\scenarios'}),{status:200,headers:{'Content-Type':'application/json'}}));
                return originalFetch(url, options);
            };
        }""")
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')
        page.wait_for_function('() => document.querySelector("#scenario-storage-note").textContent.includes("No JSON scenarios found")')
        assert not page.locator('#new-line-btn').is_disabled()
        assert 'Old draft' not in page.locator('#status-text').inner_text() or 'blank line' in page.locator('#status-text').inner_text()
        assert page.evaluate("sessionStorage.getItem('capstone-builder-draft-unrestored')")
        assert len(page.evaluate("Object.keys(window.__builderTest.serializeScenario().boxes)")) == 3
        page.locator('#new-line-btn').click()
        assert 'New blank line created' in page.locator('#status-text').inner_text()
        assert not errors, errors
        browser.close()
    print('Chromium: broken draft recovery, JSON folder diagnosis, New Line reset passed.')

if __name__ == '__main__':
    check()
