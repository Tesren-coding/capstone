"""Canvas snapping, dimensions, group translation and guide-only transient UI state.
Run: python tests/browser_smart_guides.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML,BUNDLE,FETCH_STUB

TEST_HOOK = r'''
window.__guideTest={
  install:()=>{
    // Isolate station-to-station snapping from the newly centered blank-line artifacts.
    Object.values(scenario.boxes).forEach((box,i)=>{box.x=25;box.y=20+i*100});
    const id1=String(createStation(1475,648));
    const id2=String(createStation(1900,648));
    drawFrame();return {id1,id2};
  },
  snapshot:()=>JSON.parse(JSON.stringify(serializeScenario())),
  guides:()=>smartGuideData?JSON.parse(JSON.stringify(smartGuideData)):null,
  select:(items)=>setSelectedKeys(items),
  meter: (px)=>meterLabel(px,Number(scaleInput.value)),
};
'''

def check():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1450,'height':1000})
        errors=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE+TEST_HOOK)
        page.wait_for_selector('body[data-builder-ready="true"]')
        assert page.locator('#smart-guide-toggle').is_checked()
        canvas=page.locator('#builder-canvas')
        canvas.scroll_into_view_if_needed()

        def where(x,y,z=1):
            b=canvas.bounding_box()
            return (b['x']+(x*z+1200*(1-z))*b['width']/2400,
                    b['y']+(y*z+521*(1-z))*b['height']/1042)
        def move(x,y,z=1): page.mouse.move(*where(x,y,z))
        def drag(start,end,z=1):
            move(*start,z);page.mouse.down();move(*end,z)
            guide=page.evaluate('window.__guideTest.guides()')
            page.mouse.up()
            assert page.evaluate('window.__guideTest.guides()') is None
            return guide
        ids=page.evaluate('window.__guideTest.install()')
        def pos(id): return page.evaluate('window.__guideTest.snapshot()')["stations"][id]
        one=pos(ids['id1']);two=pos(ids['id2'])
        assert abs(one['x']-1400)<1 and two['x']>1700
        # Drag second station close to the first station's right-hand dock.
        # Target x=1400+150+22=1572; mouse offset 20,30.
        desired=1577
        guide=drag((two['x']+20,two['y']+35), (desired+20,two['y']+35))
        assert abs(pos(ids['id2'])['x']-1572)<1,pos(ids['id2'])
        assert guide is not None and any(g['kind']=='gap' and g['axis']=='x' for g in guide['guides']),guide
        assert any(abs(m['distance']-22)<0.1 for m in guide['measurements']),guide
        assert page.evaluate('window.__guideTest.meter(22)')=='0.44 m'
        assert 'smartGuideData' not in page.evaluate('window.__guideTest.snapshot()')

        # Shift the unit scale and confirm displayed values are converted, not geometry.
        page.locator('#layout-scale-input').fill('100')
        assert page.evaluate('window.__guideTest.meter(22)')=='0.22 m'
        assert abs(pos(ids['id2'])['x']-1572)<1

        # Disable guide/snap: a near alignment must no longer adjust coordinates.
        page.locator('#smart-guide-toggle').uncheck()
        x=pos(ids['id2'])['x']
        guide=drag((x+20,two['y']+35),(x+20+6,two['y']+35))
        assert abs(pos(ids['id2'])['x']-(x+6))<1.5,pos(ids['id2'])
        assert guide is None
        page.locator('#smart-guide-toggle').check()

        # Repeat at 125% zoom; snapping tolerance remains in screen pixels.
        page.locator('[data-zoom-in]').click()
        x=pos(ids['id2'])['x']
        guide=drag((x+20,two['y']+35),(x+20-6,two['y']+35),1.25)
        assert abs(pos(ids['id2'])['x']-1572)<1.5,pos(ids['id2'])
        assert guide is not None

        # Multi-select remains possible, and group movement keeps station spacing.
        # Move away from all alignment targets to avoid purposeful snapping.
        page.evaluate(f'''window.__guideTest.select(['station:{ids['id1']}','station:{ids['id2']}']);drawFrame();''')
        a=pos(ids['id1']);b=pos(ids['id2'])
        guide=drag((a['x']+25,a['y']+30),(a['x']+95,a['y']+100),1.25)
        a2=pos(ids['id1']);b2=pos(ids['id2'])
        assert abs((b2['x']-a2['x'])-(b['x']-a['x']))<.01
        assert abs((b2['y']-a2['y'])-(b['y']-a['y']))<.01
        assert not errors,errors
        print('Chromium: smart dock, guide meters, px/m change, toggle off, zoom, group spacing and cleanup passed.')
        browser.close()

if __name__=='__main__': check()
