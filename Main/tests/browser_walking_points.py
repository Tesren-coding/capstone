"""Browser check for operator-wide, per-station standing points.
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
        // The operator works at S1, transfers from S1 to S2 and back.
        scenario.operators[opId].sequence = [
            {action:'work',loc:sid,process:'p1'},
            {action:'pick',loc:sid},
            {action:'drop',loc:otherSid},
            {action:'pick',loc:otherSid},
            {action:'drop',loc:sid},
        ];
        const secondId=createOperator(1180, 300);
        scenario.operators[secondId].sequence=[{action:'work',loc:sid,process:'p1'}];
        setSelectedKeys([selectionKey('operator',opId)]);
        drawFrame();
        return {sid, otherSid, opId, secondId};
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
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1450, 'height':1000})
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
        def mouse_at(x,y,zoom=1):
            box=canvas.bounding_box()
            return (box['x']+(x*zoom+1200*(1-zoom))*box['width']/2400,
                    box['y']+(y*zoom+521*(1-zoom))*box['height']/1042)
        def click_world(x,y,zoom=1):
            page.mouse.click(*mouse_at(x,y,zoom))
        info=page.evaluate('window.__walkingTest.install()')
        assert page.locator('.step-standing-select').count()==0
        assert page.locator('.task-standing-select').count()==0
        assert page.locator('.operator-station-standing').count()==2
        slots=page.evaluate('window.__walkingTest.standingSlots()')
        assert len(slots)==8 and {s['stationId'] for s in slots}=={info['sid'],info['otherSid']}, slots
        # One click at S1 changes ALL three references to that station.
        first=next(s for s in slots if s['stationId']==info['sid'] and s['side']=='right')
        click_world(first['x'],first['y'])
        steps=page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]['sequence']
        assert [steps[i]['standing_side'] for i in (0,1,4)]==['right']*3, steps
        assert not any('standing_side' in steps[i] for i in (2,3)), steps
        # Another station is configurable immediately; no process selection.
        second=next(s for s in slots if s['stationId']==info['otherSid'] and s['side']=='bottom')
        click_world(second['x'],second['y'])
        steps=page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]['sequence']
        assert [steps[i]['standing_side'] for i in (2,3)]==['bottom']*2, steps
        assert page.locator('.operator-station-standing').count()==2
        assert page.locator('.operator-standing-auto:not([disabled])').count()==2
        # Sides are operator-specific, NOT stored on the shared station.
        page.evaluate('(id) => window.__walkingTest.activateOperator(id)',info['secondId'])
        slots=page.evaluate('window.__walkingTest.standingSlots()')
        assert len(slots)==4 and {s['stationId'] for s in slots}=={info['sid']}
        left=next(s for s in slots if s['side']=='left')
        click_world(left['x'],left['y'])
        operators=page.evaluate('window.__walkingTest.snapshot()')['operators']
        assert operators[info['secondId']]['sequence'][0]['standing_side']=='left'
        assert operators[info['opId']]['sequence'][0]['standing_side']=='right'
        # Selection of a station does not display standing-point rings.
        station=page.evaluate('window.__walkingTest.snapshot()')['stations'][info['sid']]
        click_world(station['x']+30,station['y']+25)
        assert page.evaluate('window.__walkingTest.selected()')==['station:'+info['sid']]
        assert page.evaluate('window.__walkingTest.standingSlots()')==[]
        # Clicking the actual operator icon activates ALL its standing rings.
        operator=page.evaluate('([id]) => window.__walkingTest.snapshot().operators[id]',[info['opId']])
        click_world(operator['x'],operator['y'])
        assert page.evaluate('window.__walkingTest.selected()')==['operator:'+info['opId']]
        assert len(page.evaluate('window.__walkingTest.standingSlots()'))==8
        # Then verify zoom-aware standing-point clicks.
        page.locator('[data-zoom-in]').click()
        assert page.locator('[data-zoom-label]').inner_text()=='125%'
        slots=page.evaluate('window.__walkingTest.standingSlots()')
        assert len(slots)==8
        top=next(s for s in slots if s['stationId']==info['sid'] and s['side']=='top')
        click_world(top['x'],top['y'],1.25)
        steps=page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]['sequence']
        assert all(steps[i]['standing_side']=='top' for i in (0,1,4))
        # Operator can still be dragged from a coincident home/standing ring.
        page.mouse.move(*mouse_at(top['x'],top['y'],1.25))
        page.mouse.down()
        page.mouse.move(*mouse_at(top['x']+70,top['y']-45,1.25),steps=10)
        page.mouse.up()
        op=page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]
        assert 'attached_to' not in op, op
        assert abs(op['x']-(top['x']+70))<3,op
        # Standing-point changes survive save/load with the original schema.
        page.locator('#layout-scale-input').fill('60')
        page.locator('#walk-speed-input').fill('1.4')
        saved=page.evaluate('window.__walkingTest.snapshot()')
        page.evaluate('(value) => window.__walkingTest.load(value)',saved)
        assert page.input_value('#layout-scale-input')=='60'
        assert page.input_value('#walk-speed-input')=='1.4'
        assert page.evaluate('window.__walkingTest.snapshot()')==saved
        page.evaluate('(id) => window.__walkingTest.activateOperator(id)',info['opId'])
        page.locator('.operator-standing-auto[data-standing-station="'+info['sid']+'"]',).click()
        steps=page.evaluate('window.__walkingTest.snapshot()')['operators'][info['opId']]['sequence']
        assert all('standing_side' not in steps[i] for i in (0,1,4)),steps
        assert all(steps[i]['standing_side']=='bottom' for i in (2,3)),steps
        # Boxes have no side circles.
        page.evaluate('(id) => window.__walkingTest.boxStepOnly(id)',info['opId'])
        assert page.evaluate('window.__walkingTest.standingSlots()')==[]
        assert page.locator('.operator-station-standing').count()==0
        page.on('dialog', lambda dialog:dialog.accept())
        page.click('#new-line-btn')
        assert page.input_value('#layout-scale-input')=='50'
        assert page.input_value('#walk-speed-input')=='1.2'
        assert page.evaluate('window.__walkingTest.snapshot()')['operators']=={}
        assert errors==[],errors
        browser.close()
    print('Chromium: multi-station operator standing dots, grouped picks/works/drops, multi-operator isolation, zoom, drag, Auto, save/load, New Line passed.')

if __name__=='__main__': check()
