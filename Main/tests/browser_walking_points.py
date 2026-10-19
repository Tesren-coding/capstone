"""Browser interaction: choose station standing points on canvas; box destinations stay unconfigured.
Run: python tests/browser_walking_points.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB

TEST_HOOK = r'''
window.__walkingTest = {
    install: () => {
        const sid = String(createStation(1490, 490));
        const otherSid = String(createStation(1920, 680));
        const first = scenario.stations[sid];
        const opId = createOperator(first.x + first.w/2, first.y - 26);
        scenario.operators[opId].sequence.push({action:'work',loc:sid,process:'p1'});
        scenario.operators[opId].sequence.push({action:'pick',loc:otherSid});
        setSelectedKeys([selectionKey('operator',opId)]);
        drawFrame();
        return {sid, otherSid, opId};
    },
    snapshot: () => JSON.parse(JSON.stringify(serializeScenario())),
    load: value => applyLoadedScenario(value),
    standingSlots: () => activeStandingSlots().map(s => ({...s})),
    selected: () => [...selectedKeys],
    activateOperator: id => setSelectedKeys([selectionKey('operator',id)]),
    boxStepOnly: id => {
        const boxId=Object.keys(scenario.boxes).find(key => scenario.boxes[key].type==='in');
        scenario.operators[id].sequence=[{action:'pick',loc:boxId}];
        setSelectedKeys([selectionKey('operator',id)]);
        renderSequenceList(scenario.operators[id]);drawFrame();
        return boxId;
    },
};
'''


def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1450,'height':1000})
        errors=[]
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE+TEST_HOOK)
        page.wait_for_selector('body[data-builder-ready="true"]')
        assert page.input_value('#layout-scale-input')=='50'
        assert page.input_value('#walk-speed-input')=='1.2'
        canvas=page.locator('#builder-canvas')
        canvas.scroll_into_view_if_needed()
        def mouse_at(x,y,scale=1):
            box=canvas.bounding_box()
            return (box['x']+(x*scale+1200*(1-scale))*box['width']/2400,
                    box['y']+(y*scale+521*(1-scale))*box['height']/1042)
        def click_world(x,y,scale=1):
            page.mouse.click(*mouse_at(x,y,scale))
        info=page.evaluate('window.__walkingTest.install()')
        assert page.locator('.step-standing-side').count()==0, 'Dropdown should be gone.'
        assert page.locator('.step-standing-select').count()==2
        assert page.locator('.step-standing-select[aria-pressed="true"]').count()==1
        slots=page.evaluate('window.__walkingTest.standingSlots()')
        assert len(slots)==4 and {s['stationId'] for s in slots}=={info['sid']},slots
        slot=next(s for s in slots if s['side']=='right')
        click_world(slot['x'],slot['y'])
        step=page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]['sequence'][0]
        assert step['standing_side']=='right',step
        page.locator('#advanced-operator-actions').evaluate('(el)=>el.open=true')
        assert 'Right' in page.locator('.sequence-step').first.inner_text()
        assert page.locator('.step-standing-auto').count()==1
        # Choose second step: ONLY its station shows the four rings.
        page.locator('#advanced-operator-actions').evaluate('(el)=>el.open=true')
        page.locator('.step-standing-select').nth(1).click()
        slots=page.evaluate('window.__walkingTest.standingSlots()')
        assert len(slots)==4 and {s['stationId'] for s in slots}=={info['otherSid']},slots
        slot=next(s for s in slots if s['side']=='bottom')
        click_world(slot['x'],slot['y'])
        steps=page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]['sequence']
        assert steps[0]['standing_side']=='right' and steps[1]['standing_side']=='bottom',steps
        # A station selection never displays these rings.
        station=page.evaluate('window.__walkingTest.snapshot()')['stations'][info['sid']]
        click_world(station['x']+30,station['y']+25)
        assert page.evaluate('window.__walkingTest.selected()')==['station:'+info['sid']]
        assert page.evaluate('window.__walkingTest.standingSlots()')==[]
        # Re-select and test zoom-aware mouse click.
        page.evaluate('(id) => window.__walkingTest.activateOperator(id)',info['opId'])
        page.locator('[data-zoom-in]').click()
        assert page.locator('[data-zoom-label]').inner_text()=='125%'
        slots=page.evaluate('window.__walkingTest.standingSlots()')
        assert len(slots)==4 and {s['stationId'] for s in slots}=={info['sid']}
        left=next(s for s in slots if s['side']=='left')
        click_world(left['x'],left['y'],1.25)
        steps=page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]['sequence']
        assert steps[0]['standing_side']=='left' and steps[1]['standing_side']=='bottom',steps
        # Still able to drag operator from its home ring, even if this is also
        # a selectable standing point (choose the top dot first).
        top=next(s for s in slots if s['side']=='top')
        click_world(top['x'],top['y'],1.25)
        assert page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]['sequence'][0]['standing_side']=='top'
        page.mouse.move(*mouse_at(top['x'],top['y'],1.25))
        page.mouse.down()
        page.mouse.move(*mouse_at(top['x']+70,top['y']-45,1.25),steps=10)
        page.mouse.up()
        updated=page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]
        assert 'attached_to' not in updated,updated
        assert abs(updated['x']-(top['x']+70))<3,updated
        # Scale and speed survive save/load, as do standing-side choices.
        page.locator('#layout-scale-input').fill('60')
        page.locator('#walk-speed-input').fill('1.4')
        saved=page.evaluate('window.__walkingTest.snapshot()')
        page.evaluate('(value) => window.__walkingTest.load(value)',saved)
        assert page.input_value('#layout-scale-input')=='60'
        assert page.input_value('#walk-speed-input')=='1.4'
        assert page.evaluate('window.__walkingTest.snapshot()')==saved
        page.evaluate('(id) => window.__walkingTest.activateOperator(id)',info['opId'])
        page.locator('#advanced-operator-actions').evaluate('(el)=>el.open=true')
        page.locator('.step-standing-auto').first.click()
        assert 'standing_side' not in page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]['sequence'][0]
        # Boxes have no dotted side-selection and don't receive standing_side.
        page.evaluate('(id) => window.__walkingTest.boxStepOnly(id)',info['opId'])
        assert page.evaluate('window.__walkingTest.standingSlots()')==[]
        assert page.locator('.step-standing-select').count()==0
        assert page.locator('.step-standing-side').count()==0
        page.on('dialog', lambda dialog:dialog.accept())
        page.click('#new-line-btn')
        assert page.input_value('#layout-scale-input')=='50'
        assert page.input_value('#walk-speed-input')=='1.2'
        assert page.evaluate('window.__walkingTest.snapshot()')['operators']=={}
        assert errors==[],errors
        browser.close()
    print('Chromium: clickable station-side rings, only assigned station visible, zoom, drag, Auto, saved positions, box centers unchanged, New Line passed.')

if __name__=='__main__': check()
