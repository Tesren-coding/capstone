"""Device-file fallback works even when remote HTTP blocks folder access.

Run: python tests/browser_remote_http_device_files.py
"""
import json
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB


def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
                                    args=['--no-sandbox'])
        page = browser.new_page(accept_downloads=True, viewport={'width':1450,'height':950})
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        # Simulate a prior user's preference for Local Folder, but a newly
        # hosted HTTP page that does not have access to showDirectoryPicker.
        page.evaluate('''() => {
            localStorage.setItem('capstone-builder-scenario-save-location', 'local');
            Object.defineProperty(window, 'isSecureContext', {configurable:true, value:false});
            window.showDirectoryPicker = undefined;
        }''')
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')
        assert page.locator('#save-location-mode').input_value() == 'download'
        assert page.locator('option[value="local"]').is_disabled()
        assert 'HTTPS' in page.locator('#local-folder-status').inner_text()
        assert page.locator('#open-device-file-btn').is_visible()
        assert page.locator('#choose-local-folder-btn').is_hidden()

        # A local file chooser works on HTTP. It does not create a server save.
        scenario = page.evaluate('window.__builderTest.serializeScenario()')
        scenario['takt_time'] = 19
        with page.expect_file_chooser() as event:
            page.locator('#open-device-file-btn').click()
        event.value.set_files({'name': 'my-offline-line.json',
                               'mimeType': 'application/json',
                               'buffer': json.dumps(scenario).encode()})
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Imported JSON")')
        current = page.evaluate('window.__builderTest.serializeScenario()')
        assert current['takt_time'] == 19
        assert page.evaluate('Object.keys(window.__savedByTest).length') == 0

        page.on('dialog', lambda dialog: dialog.accept('my-updated-line'))
        with page.expect_download() as download:
            page.locator('#save-scenario-btn').click()
        assert download.value.suggested_filename == 'my-updated-line.json'
        assert page.evaluate('Object.keys(window.__savedByTest).length') == 0

        # Explicit Server mode still gives access to older server saves.
        page.locator('#save-location-mode').select_option('server')
        page.wait_for_function('() => document.querySelector("#scenario-storage-note").textContent.includes("storage")')
        assert page.locator('#open-device-file-btn').is_visible()
        assert not errors, errors
        browser.close()
        print('Remote HTTP fallback: open local JSON, client download, no implicit server saves passed.')


if __name__ == '__main__':
    test()
