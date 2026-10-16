"""Marquee selection, group translation, operator attachments, and extra arrows.

Run: python tests/browser_multiselect.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB, almost


def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1450, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE + '\nwindow.__selectionTest = () => [...selectedKeys];')
        page.wait_for_selector('body[data-builder-ready="true"]')
        canvas = page.locator('#builder-canvas')
        canvas.scroll_into_view_if_needed()

        def coordinates(x, y, scale=1):
            rect = canvas.bounding_box()
            assert rect
            return (rect['x'] + (x*scale+1200*(1-scale))*rect['width']/2400,
                    rect['y'] + (y*scale+521*(1-scale))*rect['height']/1042)

        def click(x, y, scale=1, modifiers=None):
            for mod in modifiers or []: page.keyboard.down(mod)
            page.mouse.click(*coordinates(x, y, scale))
            for mod in reversed(modifiers or []): page.keyboard.up(mod)

        def drag(x, y, to_x, to_y, scale=1):
            page.mouse.move(*coordinates(x, y, scale))
            page.mouse.down()
            page.mouse.move(*coordinates(to_x, to_y, scale), steps=12)
            page.mouse.up()

        def put(kind, x, y, scale=1):
            page.locator(f'.add-btn[data-type="{kind}"]').click()
            canvas.scroll_into_view_if_needed()
            click(x, y, scale)

        def snapshot():
            return page.evaluate('window.__builderTest.serializeScenario()')

        def selected():
            return set(page.evaluate('window.__selectionTest()'))

        put('station', 1500, 470)
        put('station', 1750, 470)
        stations = snapshot()['stations']
        one = stations['1']
        two = stations['2']
        assert one['w']==150 and two['w']==150
        center1 = one['x'] + 75
        top1 = one['y'] - 26
        put('operator', center1, top1)
        before = snapshot()
        op_before = before['operators']['Op1']
        assert op_before['attached_to']=={'station_id':'1', 'side':'top'}

        # A click on a station must NOT show the available operator circles.
        click(one['x']+20, one['y']+30)
        assert selected()=={'station:1'}
        def count_ring_pixels(x,y):
            return page.evaluate('''({x,y}) => {
              const c=document.getElementById('builder-canvas');
              const d=c.getContext('2d').getImageData(Math.round(x)-24,Math.round(y)-24,48,48).data;
              let found=0;
              for(let i=0;i<d.length;i+=4) if(d[i]===82 && d[i+1]===121 && d[i+2]===155) found++;
              return found;
            }''', {'x':two['x']+75, 'y':two['y']-26})
        assert count_ring_pixels(two['x']+75,two['y']-26)==0
        click(op_before['x'], op_before['y'])
        assert selected()=={'operator:Op1'}
        # With no assigned sequence step, an operator selection has no
        # standing-point rings (only the relevant step station displays them).
        assert count_ring_pixels(two['x']+75,two['y']-26)==0

        # Marquee intersects both stations and operator, but not the default arrow.
        drag(1370, 350, 1930, 620)
        assert selected()=={'station:1','station:2','operator:Op1'}, selected()
        assert '3 items selected' in page.locator('#panel-title').inner_text()
        assert page.locator('#delete-item-btn').inner_text()=='Delete 3 Selected'
        drag(center1, one['y']+60, center1+90, one['y']+130)
        after = snapshot()
        for id in ('1','2'):
            almost(after['stations'][id]['x']-before['stations'][id]['x'],90)
            almost(after['stations'][id]['y']-before['stations'][id]['y'],70)
        op_after=after['operators']['Op1']
        assert op_after['attached_to']==op_before['attached_to']
        almost(op_after['x']-op_before['x'],90)
        almost(op_after['y']-op_before['y'],70)
        assert selected()=={'station:1','station:2','operator:Op1'}

        # Ctrl-click a selected station toggles it out of the group.
        s2=after['stations']['2']
        click(s2['x']+40,s2['y']+30,modifiers=['Control'])
        assert selected()=={'station:1','operator:Op1'}
        drag(after['stations']['1']['x']+35,after['stations']['1']['y']+35,
             after['stations']['1']['x']+35+55,after['stations']['1']['y']+35+40)
        adjusted=snapshot()
        almost(adjusted['stations']['1']['x']-after['stations']['1']['x'],55)
        almost(adjusted['stations']['2']['x']-after['stations']['2']['x'],0)
        almost(adjusted['operators']['Op1']['x']-op_after['x'],55)

        # Ctrl-add / move two free boxes too, while keeping every box's metadata.
        click(1100, 930)
        assert not selected()
        page.locator('.add-btn[data-type="direction"]').click()
        click(1650,800)
        arrows=[(id,box) for id,box in snapshot()['boxes'].items() if box['type']=='direction']
        assert len(arrows)==2,arrows
        extra_id,extra=arrows[-1]
        assert (extra['w'],extra['h'])==(875,85)
        assert extra['name']=='Line Direction'
        assert extra['rotation']==0 and not extra['flip_horizontal'] and not extra['flip_vertical']
        click(extra['x']+extra['w']/2,extra['y']+extra['h']/2)
        assert selected()=={f'box:{extra_id}'}
        assert page.locator('#field-direction-width').is_visible()

        # Marquee at zoom still uses world coordinates.
        page.locator('[data-zoom-in]').click()
        assert page.locator('[data-zoom-label]').inner_text()=='125%'
        click(1100,930,1.25)
        before_count=len(selected())
        assert before_count==0
        moved1=adjusted['stations']['1']
        moved2=adjusted['stations']['2']
        x1=min(moved1['x'],moved2['x'])-15
        x2=max(moved1['x']+moved1['w'],moved2['x']+moved2['w'])+15
        y1=min(moved1['y'],moved2['y'])-50
        y2=max(moved1['y']+moved1['h'],moved2['y']+moved2['h'])+15
        drag(x1,y1,x2,y2,1.25)
        assert selected()=={'station:1','station:2','operator:Op1'}, selected()

        # Selection is view-only, not part of serialized JSON.
        assert 'selectedKeys' not in snapshot()
        page.locator('#delete-item-btn').click()
        after_delete=snapshot()
        assert not after_delete['stations'] and not after_delete['operators']
        assert len(after_delete['boxes'])==4  # the two arrows + IN + OUT
        assert not selected()
        assert not errors,errors
        print('Chromium: marquee, multi-item movement, station attachments, Ctrl-toggle, '
              'no station rings, extra direction, zoom selection passed.')
        browser.close()

if __name__=='__main__':
    check()
