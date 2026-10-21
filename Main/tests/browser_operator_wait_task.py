"""Wait task editor, duration and JSON roundtrip on the real Builder bundle."""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB


def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1500,'height':1024})
        errors=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')
        opid=page.evaluate('''() => {const opid=createOperator(780,440);
            setSelectedKeys([selectionKey('operator',opid)]);return opid;}''')
        page.locator('[data-add-task="wait"]').click()
        assert page.locator('.operator-task-card').count()==1
        assert 'Wait' in page.locator('.operator-task-card strong').inner_text()
        duration=page.locator('.task-wait-duration')
        assert duration.input_value()=='1'
        duration.fill('7.5')
        duration.dispatch_event('change')
        stored=page.evaluate('(id)=>scenario.operators[id].sequence',opid)
        assert stored==[{'action':'wait','duration':7.5}],stored
        assert page.locator('.operator-standing-list').count()==0 or not page.locator('.operator-station-standing').count()
        page.locator('[data-add-task="process"]').click()
        assert page.locator('.operator-task-card').count()==2
        snap=page.evaluate('serializeScenario()')
        page.evaluate('(s)=>applyLoadedScenario(s)',snap)
        page.evaluate('(id)=>setSelectedKeys([selectionKey("operator",id)])',opid)
        assert page.locator('.operator-task-card').count()==2
        assert page.locator('.task-wait-duration').input_value()=='7.5'
        assert page.evaluate('(id)=>scenario.operators[id].sequence[0].duration',opid)==7.5
        # Advanced action editor can also edit a Wait step without a location.
        page.locator('#advanced-operator-actions summary').click()
        assert page.locator('.step-loc').count()==1  # only the Work step has a location
        assert page.locator('.step-wait-duration').count()==1
        page.locator('.step-wait-duration').fill('3')
        page.locator('.step-wait-duration').dispatch_event('change')
        assert page.evaluate('(id)=>scenario.operators[id].sequence[0].duration',opid)==3
        assert not errors, errors
        browser.close()
    print('Chromium: deliberate Wait task, duration edit, advanced actions and scenario roundtrip passed.')


if __name__=='__main__':check()
