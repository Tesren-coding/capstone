"""Operator ID/name invariants in the real Line Builder (no Flask server required).
Run: python tests/browser_operator_id_names.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB


def check():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1450,'height':1000})
        errors=[]
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')

        assert page.evaluate('''() => {
            const ids=[createOperator(1800,100),createOperator(1900,100),createOperator(2000,100)];
            return ids.join(',')
        }''')=='Op1,Op2,Op3'
        assert page.evaluate('Object.values(scenario.operators).every(op => op.name.startsWith("Op"))')

        # Editing an operator shows a static ID, never an editable name.
        page.evaluate("setSelectedKeys([selectionKey('operator','Op3')])")
        assert page.locator('#panel-title').inner_text()=='Op3'
        assert page.locator('#field-name').count()==0

        # Deleting an operator leaves other IDs stable; add reuses the hole.
        page.evaluate('delete scenario.operators.Op2')
        assert page.evaluate('createOperator(2100,100)')=='Op2'
        assert page.evaluate('Object.keys(scenario.operators).sort().join(",")')=='Op1,Op2,Op3'

        # Clipboard copies receive new ID (not duplicated old ID/name).
        page.evaluate("setSelectedKeys([selectionKey('operator','Op1')])")
        page.keyboard.press('Control+c')
        page.keyboard.press('Control+v')
        data=page.evaluate('serializeScenario()')
        assert set(data['operators'])=={'Op1','Op2','Op3','Op4'}
        assert data['operators']['Op4']['name']=='Op4'

        # Reorder is the single control for both changing order and filling gaps.
        # No separate Renumber Operators button remains.
        assert page.locator('#renumber-operators-btn').count()==0
        page.evaluate('''() => {
            scenario.operators.Op3.sequence = [{action:'work', loc:'1'}];
            scenario.operators.Op3.color = [1, 2, 3];
            scenario.operators.Op3.name = 'Old custom name';
            delete scenario.operators.Op2;
            delete scenario.operators.Op4;
        }''')
        page.locator('#reorder-operators-btn').click()
        handle=page.locator('[data-operator-order-id="Op3"] .drag-handle')
        handle.focus()
        page.keyboard.press('Alt+ArrowUp')
        data=page.evaluate('serializeScenario()')
        assert set(data['operators'])=={'Op1','Op2'},data
        assert data['operators']['Op1']['name']=='Op1'
        assert data['operators']['Op1']['color']==[1,2,3]
        assert data['operators']['Op1']['sequence']==[{'action':'work','loc':'1'}]
        assert page.evaluate('scenario.operators.Op1.name')=='Op1'

        # Legacy custom names are normalized in memory; IDs and settings stay.
        page.evaluate('''() => {
            const old = structuredClone(serializeScenario());
            old.operators.Op1.name='Alice';
            old.operators.Op2.name='Bob';
            applyLoadedScenario(old);
        }''')
        assert page.evaluate('Object.entries(scenario.operators).every(([id,op]) => id === op.name)')
        page.evaluate("setSelectedKeys([selectionKey('operator','Op1')])")
        assert page.locator('#panel-title').inner_text()=='Op1'
        assert page.locator('#field-name').count()==0
        assert not errors,errors
        print('Chromium operator naming, ID reuse, clipboard, reorder-only and legacy load: passed.')
        browser.close()


if __name__=='__main__': check()
