"""Browser regression for starting-part Processed / Not Processed selector.
Run: python tests/browser_starting_part_status.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB

HOOK = '''window.__statusTest = {
  snapshot:()=>structuredClone(serializeScenario()),
  select:(id)=>setSelectedKeys([`station:${id}`]),
  reload:(data)=>applyLoadedScenario(data),
};'''


def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
                                    args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1500, 'height': 1024})
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE + HOOK)
        page.wait_for_selector('body[data-builder-ready="true"]')
        page.evaluate('''() => {
          scenario.stations['1'] = {x:320,y:290,w:150,h:96,name:'S1',
            processes:[{id:'p1',name:'Inspect',manual_time:1,auto_time:0}],has_part:false};
          window.__statusTest.select('1'); drawFrame();
        }''')
        starting = page.locator('#starting-part-status')
        selector = page.locator('#field-starting-part-processed')
        assert selector.count() == 1
        assert not starting.is_visible()
        page.locator('#field-haspart').check()
        assert starting.is_visible()
        assert selector.input_value() == 'unprocessed'
        assert page.evaluate('window.__statusTest.snapshot().stations["1"].starting_part_processed') is not True
        selector.select_option('processed')
        assert page.evaluate('window.__statusTest.snapshot().stations["1"].starting_part_processed') is True
        # Save/load / Undo-style restore retains the chosen state.
        snapshot = page.evaluate('window.__statusTest.snapshot()')
        page.evaluate('window.__statusTest.reload', snapshot)
        page.evaluate('window.__statusTest.select("1")')
        assert page.locator('#field-starting-part-processed').input_value() == 'processed'
        # Removing the part resets its status, so re-enabling does not silently
        # mark a newly configured starting part as already processed.
        page.locator('#field-haspart').uncheck()
        assert not page.locator('#starting-part-status').is_visible()
        assert page.evaluate('window.__statusTest.snapshot().stations["1"].starting_part_processed') is False
        page.locator('#field-haspart').check()
        assert page.locator('#field-starting-part-processed').input_value() == 'unprocessed'
        assert not errors, errors
        browser.close()
    print('Chromium: starting part status selection, save/load, and reset passed.')


if __name__ == '__main__':
    check()
