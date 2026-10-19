"""Test New Line, direction marker editor, resizing/rotation/flip and save/load.
Run: python tests/browser_new_line_direction.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB, almost


def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1450,'height':1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')
        canvas = page.locator('#builder-canvas')
        canvas.scroll_into_view_if_needed()

        def data():
            return page.evaluate('window.__builderTest.serializeScenario()')

        def point(x,y,scale=1):
            offset_x=1200*(1-scale); offset_y=521*(1-scale)
            rect=canvas.bounding_box()
            assert rect
            return (rect['x']+(x*scale+offset_x)*rect['width']/2400,
                    rect['y']+(y*scale+offset_y)*rect['height']/1042)

        def click(x,y,scale=1):
            page.mouse.click(*point(x,y,scale))

        def drag(x,y,tx,ty,scale=1):
            page.mouse.move(*point(x,y,scale))
            page.mouse.down()
            page.mouse.move(*point(tx,ty,scale),steps=10)
            page.mouse.up()

        # A fresh line contains only the three artifacts, with no stations/operators.
        initial = data()
        assert not initial['stations'] and not initial['operators']
        assert sorted(b['type'] for b in initial['boxes'].values()) == ['direction','in','out']
        marker_id, marker = next((k,v) for k,v in initial['boxes'].items() if v['type']=='direction')
        raw = next(b for b in initial['boxes'].values() if b['type'] == 'in')
        finished = next(b for b in initial['boxes'].values() if b['type'] == 'out')
        assert (marker['w'], marker['h']) == (875, 85), marker
        # The full three-object group is now centered dynamically on the canvas.
        assert (marker['x'], marker['y']) == (705, 478.5), marker
        assert (raw['x'], raw['y']) == (1605, 443.5), raw
        assert (finished['x'], finished['y']) == (1605, 538.5), finished
        group_x=(marker['x']+finished['x']+finished['w'])/2
        group_y=(raw['y']+finished['y']+finished['h'])/2
        assert (group_x,group_y)==(1200,521)
        assert raw['x'] > marker['x'] + marker['w'] and raw['y'] < finished['y']
        assert marker['rotation']==0 and not marker['flip_horizontal'] and not marker['flip_vertical']
        click(marker['x']+marker['w']/2, marker['y']+marker['h']/2)
        assert page.locator('#field-direction-width').is_visible()
        page.locator('#field-direction-width').fill('300')
        page.locator('#field-direction-width').press('Tab')
        page.locator('#field-direction-height').fill('48')
        page.locator('#field-direction-height').press('Tab')
        marker = data()['boxes'][marker_id]
        assert (marker['w'],marker['h']) == (300,48)
        page.locator('#flip-direction-horizontal').click()
        page.locator('#flip-direction-vertical').click()
        assert data()['boxes'][marker_id]['flip_horizontal'] is True
        assert data()['boxes'][marker_id]['flip_vertical'] is True
        page.locator('#rotate-direction-right').click()
        assert data()['boxes'][marker_id]['rotation']==90
        page.locator('#field-direction-rotation').fill('180')
        page.locator('#field-direction-rotation').press('Tab')
        assert data()['boxes'][marker_id]['rotation']==180
        page.locator('#rotate-direction-left').click()
        assert data()['boxes'][marker_id]['rotation']==90

        # Move the rotated marker, then use the canvas handle while zoomed.
        marker = data()['boxes'][marker_id]
        cx=marker['x']+marker['w']/2;cy=marker['y']+marker['h']/2
        drag(cx,cy,cx+80,cy+80)
        moved=data()['boxes'][marker_id]
        almost(moved['x'],marker['x']+80)
        almost(moved['y'],marker['y']+80)
        page.locator('[data-zoom-in]').click()
        assert page.locator('[data-zoom-label]').inner_text()=='125%'
        # rotation=90: handle (cx-h/2,cy+w/2). Drag farther left/down.
        cx=moved['x']+moved['w']/2; cy=moved['y']+moved['h']/2
        hx=cx-moved['h']/2; hy=cy+moved['w']/2
        drag(hx,hy,hx-12,hy+40,1.25)
        resized=data()['boxes'][marker_id]
        assert resized['w']>moved['w'] and resized['h']>moved['h'],(moved,resized)

        # Save and restore marker metadata through the same payload used by SQL.
        dialog_mode={'value':'accept'}
        def handle_dialog(dialog):
            if dialog_mode['value']=='dismiss': dialog.dismiss()
            elif dialog.type=='prompt': dialog.accept('direction-check')
            else: dialog.accept()
        page.on('dialog',handle_dialog)
        page.locator('#save-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Saved")')
        saved=page.evaluate('window.__savedByTest["direction-check.json"]')
        assert saved['boxes'][marker_id]==resized

        # The New Line action must not overwrite the saved SQL document.
        page.locator('#new-line-btn').click()
        blank=data()
        assert not blank['stations'] and not blank['operators']
        assert sorted(b['type'] for b in blank['boxes'].values())==['direction','in','out']
        default_marker = next(b for b in blank['boxes'].values() if b['type']=='direction')
        assert (default_marker['x'], default_marker['y'], default_marker['w'], default_marker['h']) == (705, 478.5, 875, 85)
        assert default_marker['rotation']==0
        assert page.evaluate('window.__savedByTest["direction-check.json"]')==saved
        assert page.locator('#scenario-select').input_value()==''
        assert page.locator('[data-zoom-label]').inner_text()=='100%'

        # Load saved scenario normally; all rotation and flip settings return.
        page.locator('#scenario-select').select_option('direction-check.json')
        page.locator('#load-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Loaded")')
        assert data()==saved

        # Making unsaved changes triggers confirmation; cancel keeps data.
        page.locator('.add-btn[data-type="station"]').click()
        click(820,470)
        before=data()
        dialog_mode['value']='dismiss'
        page.locator('#new-line-btn').click()
        assert data()==before
        dialog_mode['value']='accept'
        page.locator('#new-line-btn').click()
        assert not data()['stations']
        assert page.evaluate('window.__savedByTest["direction-check.json"]')==saved
        assert not errors, errors
        print('Chromium: default line, direction size/rotate/flip/drag, zoom resize, save/load, new-line cancel/confirm passed.')
        browser.close()


if __name__ == '__main__':
    check()
