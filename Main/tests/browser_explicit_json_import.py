"""The visible Import JSON button works on server-hosted HTTP without server saves.

Run: python tests/browser_explicit_json_import.py
"""
import json
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB


def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
                                    args=['--no-sandbox'])
        page = browser.new_page(accept_downloads=True, viewport={'width': 1450, 'height': 950})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.evaluate('''() => {
            Object.defineProperty(window, 'isSecureContext', {configurable: true, value: false});
            window.showDirectoryPicker = undefined;
        }''')
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')
        button = page.locator('#open-device-file-btn')
        assert button.inner_text().strip() == 'Import JSON…'
        assert button.is_visible()
        assert page.locator('#save-location-mode').input_value() == 'server'

        initial = page.evaluate('window.__builderTest.serializeScenario()')
        scenario = json.loads(json.dumps(initial))
        scenario['takt_time'] = 27
        scenario['line_name'] = 'My imported line'

        with page.expect_file_chooser() as chooser:
            button.click()
        chooser.value.set_files({'name': 'production-line.json', 'mimeType': 'application/json',
                                 'buffer': json.dumps(scenario).encode('utf8')})
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Imported JSON")')
        result = page.evaluate('window.__builderTest.serializeScenario()')
        assert result['takt_time'] == 27
        assert page.locator('#save-location-mode').input_value() == 'download'
        assert page.evaluate('Object.keys(window.__savedByTest).length') == 0
        assert page.locator('#status-text').inner_text().find('No server save was created') != -1

        # Invalid syntax does not clear the previous scenario and can be retried.
        page.locator('#import-scenario-file').set_input_files({
            'name': 'broken.json', 'mimeType': 'application/json', 'buffer': b'{bad'
        })
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("JSON import failed")')
        assert page.evaluate('window.__builderTest.serializeScenario().takt_time') == 27
        assert button.is_enabled()

        # A JSON array is not a scenario document.
        page.locator('#import-scenario-file').set_input_files({
            'name': 'array.json', 'mimeType': 'application/json', 'buffer': b'[]'
        })
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("does not contain")')
        assert page.evaluate('window.__builderTest.serializeScenario().takt_time') == 27

        # Rejecting an overwrite confirmation must preserve unsaved changes.
        next_scenario = json.loads(json.dumps(initial))
        next_scenario['takt_time'] = 40
        page.on('dialog', lambda dialog: dialog.dismiss())
        page.locator('#import-scenario-file').set_input_files({
            'name': 'another.json', 'mimeType': 'application/json',
            'buffer': json.dumps(next_scenario).encode('utf8')
        })
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("cancelled")')
        assert page.evaluate('window.__builderTest.serializeScenario().takt_time') == 27
        assert page.evaluate('Object.keys(window.__savedByTest).length') == 0
        assert not errors, errors
        browser.close()
        print('Import JSON: HTTP file picker, validate, preserve on failure/cancel, no server saves passed.')


if __name__ == '__main__':
    test()
