"""Test Rename Scenario in the actual Line Builder frontend (mocked backend).
Run: python tests/browser_rename_scenario.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB


def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1450, 'height': 1000})
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')

        def scenario():
            return page.evaluate('window.__builderTest.serializeScenario()')

        # Save a fresh line then add a new unsaved change.
        responses = []
        def dialog(d):
            responses.append(d.message)
            if d.type == 'prompt':
                d.accept('First Line' if len([x for x in responses if 'Enter a name' in x]) == 1 else 'Second Line')
            else:
                d.accept()
        page.on('dialog', dialog)
        page.locator('#save-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Saved")')
        assert page.locator('#scenario-select').input_value() == 'First_Line.json'
        filename = page.locator('#scenario-select').input_value()
        initial = scenario()
        # Change the canvas: rename must NOT autosave it.
        page.locator('.add-btn[data-type="station"]').click()
        canvas = page.locator('#builder-canvas')
        canvas.scroll_into_view_if_needed()
        rect = canvas.bounding_box()
        page.mouse.click(rect['x'] + 400 * rect['width'] / 2400, rect['y'] + 320 * rect['height'] / 1042)
        changed = scenario()
        assert changed != initial

        # Rename loaded save and preserve local (unsaved) edits.
        page.remove_listener('dialog', dialog)
        def rename_dialog(d): d.accept('Renamed Line')
        page.on('dialog', rename_dialog)
        page.locator('#rename-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Renamed")')
        assert page.locator('#scenario-select').input_value() == 'Renamed_Line.json'
        assert scenario() == changed
        stored = page.evaluate('window.__savedByTest')
        assert filename not in stored
        assert stored['Renamed_Line.json'] == initial

        # Save canvas edits under renamed scenario (not the old filename).
        page.locator('#save-scenario-btn').click()
        page.locator('#save-overwrite-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Saved")')
        stored = page.evaluate('window.__savedByTest')
        assert stored['Renamed_Line.json'] == changed
        assert filename not in stored

        # Missing selection produces a clear message and no mutation.
        page.locator('#scenario-select').select_option('')
        page.locator('#rename-scenario-btn').click()
        assert 'Select a saved scenario' in page.locator('#status-text').inner_text()
        assert page.evaluate('window.__savedByTest["Renamed_Line.json"]') == changed

        # Rename a different selected save, without changing the one loaded in
        # the editor. Duplicate names must never overwrite an existing save.
        page.remove_listener('dialog', rename_dialog)
        page.locator('#new-line-btn').click()
        page.on('dialog', lambda d: d.accept('Second Line'))
        page.locator('#save-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Saved")')
        second = page.evaluate('window.__savedByTest["Second_Line.json"]')
        page.locator('#scenario-select').select_option('Renamed_Line.json')
        page.locator('#rename-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Rename failed")')
        assert 'already exists' in page.locator('#status-text').inner_text()
        assert page.evaluate('window.__savedByTest["Second_Line.json"]') == second
        assert page.evaluate('window.__savedByTest["Renamed_Line.json"]') == changed
        assert not errors, errors
        browser.close()
        print('Chromium: rename, unsaved edits, save, duplicate conflict and empty selection passed.')


if __name__ == '__main__':
    test()
