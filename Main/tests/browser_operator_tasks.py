"""Browser task cards should compile into old actions without breaking save/load.
Run: python tests/browser_operator_tasks.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB


def check():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1450,'height':1000})
        errors=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')
        data=page.evaluate('''() => {
            const station=createStation(1850,500);
            const transfer=createOperator(1500,400);
            const process=createOperator(1600,400);
            const outbound=createOperator(1700,400);
            setSelectedKeys([selectionKey('operator',transfer)]);
            return {station,transfer,process,outbound,
                input:Object.keys(scenario.boxes).find(id=>scenario.boxes[id].type==='in'),
                output:Object.keys(scenario.boxes).find(id=>scenario.boxes[id].type==='out')};
        }''')
        assert page.locator('#operator-task-list').count()==1
        page.locator('[data-add-task="transfer"]').click()
        assert page.locator('.operator-task-card').count()==1
        page.locator('.task-field[data-field="source"]').select_option(data['input'])
        page.locator('.task-field[data-field="target"]').select_option(str(data['station']))
        first=page.evaluate('(id) => scenario.operators[id].sequence',data['transfer'])
        assert [s['action'] for s in first]==['pick','drop'],first
        assert [s['loc'] for s in first]==[data['input'],str(data['station'])]

        page.evaluate('(id) => setSelectedKeys([selectionKey("operator",id)])',data['process'])
        page.locator('[data-add-task="process"]').click()
        page.locator('.task-field[data-field="station"]').select_option(str(data['station']))
        assert page.evaluate('(id) => scenario.operators[id].sequence[0].process',data['process'])=='p1'
        assert page.locator('.task-standing-select').count()==1
        page.evaluate('(id) => setSelectedKeys([selectionKey("operator",id)])',data['outbound'])
        page.locator('[data-add-task="transfer"]').click()
        page.locator('.task-field[data-field="source"]').select_option(str(data['station']))
        page.locator('.task-field[data-field="target"]').select_option(data['output'])
        scenario=page.evaluate('serializeScenario()')
        assert [s['loc'] for s in scenario['operators'][data['outbound']]['sequence']]==[str(data['station']),data['output']]
        page.evaluate('(scenario)=>applyLoadedScenario(scenario)',scenario)
        page.evaluate('(id)=>setSelectedKeys([selectionKey("operator",id)])',data['process'])
        assert page.locator('.operator-task-card').count()==1
        assert page.locator('.operator-task-card strong').first.inner_text().endswith('Process part')
        # Full cycle remains one easy-to-understand card, while stored actions remain stable.
        page.evaluate('''(d) => {
            scenario.operators[d.process].sequence=[
                {action:'pick',loc:d.input},{action:'drop',loc:d.station},
                {action:'work',loc:d.station,process:'p1'},
                {action:'pick',loc:d.station},{action:'drop',loc:d.output}];
            setSelectedKeys([selectionKey('operator',d.process)]);
        }''',data)
        assert page.locator('.operator-task-card').count()==1
        assert 'Collect' in page.locator('.operator-task-card strong').first.inner_text()
        assert len(page.evaluate('(id)=>scenario.operators[id].sequence',data['process']))==5
        assert not errors,errors
        browser.close()
        print('Chromium: transfer/work/deliver across 3 operators, save/load and full-cycle task cards passed.')

if __name__=='__main__':check()
