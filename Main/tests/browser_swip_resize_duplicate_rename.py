"""SWIP corner and dimension resizing, canvas double-click rename, Ctrl-drag copy.
Run python tests/browser_swip_resize_duplicate_rename.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB

HOOK = """
window.__qualityTest = {
    snapshot:()=>structuredClone(serializeScenario()),
    select:(type,id)=>setSelectedKeys([`${type}:${id}`]),
    keys:()=>[...selectedKeys],
};
"""

def check():
  with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1450,'height':1000})
    errors=[]
    page.on('pageerror', lambda exc:errors.append(str(exc)))
    page.set_content(HTML)
    page.evaluate(FETCH_STUB)
    page.add_script_tag(content=BUNDLE+HOOK)
    page.wait_for_selector('body[data-builder-ready="true"]')
    canvas=page.locator('#builder-canvas')
    canvas.scroll_into_view_if_needed()
    # Isolate the fixture from the centred initial artifacts.
    page.evaluate('Object.values(scenario.boxes).forEach((box,i)=>{box.x=60;box.y=30+110*i});drawFrame()')
    def at(x,y):
      b=canvas.bounding_box()
      return (b['x']+x*b['width']/2400, b['y']+y*b['height']/1042)
    def click(x,y):page.mouse.click(*at(x,y))
    def drag(a,b,modifier=None):
      if modifier:page.keyboard.down(modifier)
      page.mouse.move(*at(*a))
      page.mouse.down()
      page.mouse.move(*at(*b),steps=12)
      page.mouse.up()
      if modifier:page.keyboard.up(modifier)
    def snap():return page.evaluate('window.__qualityTest.snapshot()')
    def keys():return set(page.evaluate('window.__qualityTest.keys()'))
    def put(kind,x,y):
      page.locator(f'.add-btn[data-type="{kind}"]').click()
      canvas.scroll_into_view_if_needed()
      click(x,y)

    put('swip',950,450)
    initial=snap()['boxes']
    bid=next(k for k,v in initial.items() if v['type']=='swip')
    box=initial[bid]
    page.evaluate('({id})=>window.__qualityTest.select("box",id)',{'id':bid})
    assert page.locator('#field-swip-width').count()==1
    assert page.locator('#field-swip-height').count()==1
    # Resize bottom-right corner, keep opposite corner fixed.
    drag((box['x']+box['w'],box['y']+box['h']),
         (box['x']+box['w']+80,box['y']+box['h']+45),'Alt')
    bigger=snap()['boxes'][bid]
    assert abs(bigger['w']-(box['w']+80))<3,(box,bigger)
    assert abs(bigger['h']-(box['h']+45))<3,(box,bigger)
    assert abs(bigger['x']-box['x'])<1 and abs(bigger['y']-box['y'])<1
    assert page.locator('#field-swip-width').input_value()==f"{bigger['w']/50:.2f}"
    page.locator('#field-swip-width').fill('4.50')
    page.locator('#field-swip-width').dispatch_event('change')
    assert abs(snap()['boxes'][bid]['w']-225)<.01
    # Double click item body to open its name input (not an ID renumber).
    box=snap()['boxes'][bid]
    page.mouse.dblclick(*at(box['x']+23,box['y']+24),delay=90)
    assert page.locator('#field-name').evaluate('(el)=>document.activeElement===el')
    page.locator('#field-name').fill('Kanban before inspection')
    assert snap()['boxes'][bid]['name']=='Kanban before inspection'
    # Station also double-click-renamable.
    put('station',1350,350)
    st=snap()['stations']['1']
    page.mouse.dblclick(*at(st['x']+25,st['y']+35),delay=90)
    assert page.locator('#field-name').evaluate('(el)=>document.activeElement===el')
    page.locator('#field-name').fill('Inspection')
    assert snap()['stations']['1']['name']=='Inspection'
    # Station selected plus Ctrl-click on SWIP creates a group; stationary Ctrl-click still works.
    page.keyboard.down('Control');click(box['x']+24,box['y']+35);page.keyboard.up('Control')
    assert keys()=={'station:1',f'box:{bid}'},keys()
    before=snap()
    # Ctrl-drag any selected item -> duplicate the WHOLE selection and move the copies.
    drag((st['x']+30,st['y']+38),(st['x']+260,st['y']+160),'Control')
    after=snap()
    assert len(after['stations'])==2,after['stations']
    assert sum(b['type']=='swip' for b in after['boxes'].values())==2
    assert after['stations']['1']==before['stations']['1']
    assert after['boxes'][bid]==before['boxes'][bid]
    assert len(keys())==2 and 'station:1' not in keys() and f'box:{bid}' not in keys(),keys()
    new_station=after['stations'][next(k for k in after['stations'] if k!='1')]
    assert new_station['x']>st['x']+150,new_station
    # Still able to undo copy in one operation.
    page.keyboard.press('Control+z')
    undone=snap()
    assert len(undone['stations'])==1 and sum(b['type']=='swip' for b in undone['boxes'].values())==1,undone
    assert not errors,errors
    browser.close()
  print('Chromium: SWIP size, double-click rename, Ctrl-click selection, Ctrl-drag duplicate group, undo passed.')

if __name__=='__main__':check()
