"""Drag-and-drop operator identity reordering: pointer, keyboard, undo, save/load.
Run: python tests/browser_reorder_operators.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB


def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1450,'height':1000})
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.on('dialog',lambda dialog: dialog.accept('ReorderedOperators'))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')

        # Each operator carries unique work assignments and colors. Operator ID is
        # its name, not a different property users can edit independently.
        page.evaluate('''() => {
          createStation(300, 300); createStation(600, 300);
          ['Op1','Op2','Op3'].forEach((_, i) => {
            const id=createOperator(1700+i*55,700);
            scenario.operators[id].sequence=[{action:'work',loc:String(i+1)}];
            scenario.operators[id].color=[40+i*45,80+i*25,120+i*12];
          });
          setSelectedKeys([selectionKey('operator','Op3')]);
          drawFrame();
        }''')
        before=page.evaluate('serializeScenario().operators')
        page.locator('#reorder-operators-btn').click()
        assert page.locator('#operator-order-panel').is_visible()
        def ids():
            return page.locator('#operator-order-list [data-operator-order-id]').evaluate_all(
                '(nodes) => nodes.map(node => node.dataset.operatorOrderId)')
        assert ids()==['Op1','Op2','Op3'],ids()
        assert page.locator('#operator-order-panel').get_attribute('hidden') is None

        # Drag Op3 above Op1 in the real UI.
        source=page.locator('[data-operator-order-id="Op3"] .drag-handle')
        target=page.locator('[data-operator-order-id="Op1"]')
        source.scroll_into_view_if_needed()
        s=source.bounding_box();t=target.bounding_box()
        assert s and t
        page.mouse.move(s['x']+s['width']/2,s['y']+s['height']/2)
        page.mouse.down()
        page.mouse.move(t['x']+t['width']/2,t['y']+5,steps=10)
        page.mouse.up()
        after=page.evaluate('serializeScenario().operators')
        assert set(after)=={'Op1','Op2','Op3'},after
        assert after['Op1']['sequence']==before['Op3']['sequence']
        assert after['Op1']['color']==before['Op3']['color']
        assert after['Op1']['x']==before['Op3']['x']
        assert after['Op2']['sequence']==before['Op1']['sequence']
        assert after['Op3']['sequence']==before['Op2']['sequence']
        assert all(id==op['name'] for id,op in after.items())
        assert page.locator('#panel-title').inner_text()=='Op1','Selected operator should follow its identity'
        assert ids()==['Op1','Op2','Op3']

        # Undo/redo work even after closing or reopening the reorder panel.
        page.keyboard.press('Control+z')
        reverted=page.evaluate('serializeScenario().operators')
        assert reverted==before,(reverted,before)
        page.keyboard.press('Control+y')
        assert page.evaluate('serializeScenario().operators')==after

        # Alt+Down should move a selected operator to next slot without pointer.
        handle=page.locator('[data-operator-order-id="Op1"] .drag-handle')
        handle.focus()
        page.keyboard.press('Alt+ArrowDown')
        swapped=page.evaluate('serializeScenario().operators')
        assert swapped['Op2']['sequence']==before['Op3']['sequence']
        assert swapped['Op1']['sequence']==before['Op1']['sequence']
        assert page.locator('#operator-order-panel').is_visible()

        # Saving to the existing scenario API writes the remapped IDs and the
        # real Load Scenario flow restores them (no storage/schema change).
        page.locator('#save-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Saved")')
        saved=page.evaluate('window.__savedByTest["ReorderedOperators.json"].operators')
        assert saved==swapped
        page.evaluate('delete scenario.operators.Op1;drawFrame()')
        page.locator('#scenario-select').select_option('ReorderedOperators.json')
        page.locator('#load-scenario-btn').click()
        page.wait_for_function('() => Object.keys(scenario.operators).length === 3')
        assert page.evaluate('serializeScenario().operators')==swapped
        assert page.locator('#operator-order-panel').is_visible()

        # Reordering a gappy legacy ID list normalizes IDs without a separate button.
        page.evaluate('''() => {delete scenario.operators.Op2;drawFrame();}''')
        assert ids()==['Op1','Op3']
        assert page.locator('#renumber-operators-btn').count()==0
        page.locator('[data-operator-order-id="Op3"] .drag-handle').focus()
        page.keyboard.press('Alt+ArrowUp')
        data=page.evaluate('serializeScenario().operators')
        assert set(data)=={'Op1','Op2'}
        assert data['Op1']['name']=='Op1' and data['Op2']['name']=='Op2'
        assert not errors,errors
        print('Chromium operator reorder: drag, identities, active selection, undo/redo, keyboard, load, gap removal passed.')
        browser.close()

if __name__=='__main__': check()
