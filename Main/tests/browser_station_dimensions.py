"""Browser regression test for station corners and saved two-point dimensions.
Run python tests/browser_station_dimensions.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB, almost

HOOK = '''
window.__dimTest={
 install:()=>{
    const sid=String(createStation(1625,605));
    const s=scenario.stations[sid];
    const oid=createOperator(s.x+s.w/2,s.y-26);
    return {sid,oid};
 },
 snapshot:()=>structuredClone(serializeScenario()),
 selectStation:id=>{setSelectedKeys([`station:${id}`]);drawFrame();},
 selectDimension:id=>{setSelectedKeys([`dimension:${id}`]);drawFrame();},
};'''

def check():
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1450,'height':1000})
  errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
  page.set_content(HTML);page.evaluate(FETCH_STUB);page.add_script_tag(content=BUNDLE+HOOK)
  page.wait_for_selector('body[data-builder-ready="true"]')
  canvas=page.locator('#builder-canvas');canvas.scroll_into_view_if_needed()
  def at(x,y,zoom=1):
   b=canvas.bounding_box()
   return (b['x']+(x*zoom+1200*(1-zoom))*b['width']/2400,
           b['y']+(y*zoom+521*(1-zoom))*b['height']/1042)
  def click(x,y,z=1):page.mouse.click(*at(x,y,z))
  def drag(a,b,z=1):
   page.mouse.move(*at(*a,z));page.mouse.down();page.mouse.move(*at(*b,z),steps=10);page.mouse.up()
  def data():return page.evaluate('window.__dimTest.snapshot()')
  ids=page.evaluate('window.__dimTest.install()');sid=ids['sid'];oid=ids['oid']
  s=data()['stations'][sid];original=dict(s)
  assert data()['operators'][oid]['attached_to']=={'station_id':sid,'side':'top'}
  page.evaluate('window.__dimTest.selectStation('+repr(sid)+')')
  assert page.locator('#field-station-width').count()==1
  # Resize from bottom-right; upper-left is anchored. Alt bypasses alignment.
  page.keyboard.down('Alt')
  drag((s['x']+s['w'],s['y']+s['h']), (s['x']+s['w']+70,s['y']+s['h']+60))
  page.keyboard.up('Alt')
  s=data()['stations'][sid]
  almost(s['x'],original['x']);almost(s['y'],original['y'])
  assert abs(s['w']-220)<5,s;assert abs(s['h']-156)<5,s
  almost(data()['operators'][oid]['x'],s['x']+s['w']/2)
  assert page.locator('#field-station-width').input_value()==f"{s['w']/50:.2f}"
  # Width typed in meters applies physical scale and keeps top-left fixed.
  page.locator('#field-station-width').fill('5.20');page.locator('#field-station-width').dispatch_event('change')
  almost(data()['stations'][sid]['w'],260)
  page.locator('#layout-scale-input').fill('100')
  # Set station back to 150 units at scale 100, and test another corner at zoom 125%.
  page.locator('#field-station-height').fill('2.00');page.locator('#field-station-height').dispatch_event('change')
  almost(data()['stations'][sid]['h'],200)
  page.locator('[data-zoom-in]').click()
  s=data()['stations'][sid]
  page.keyboard.down('Alt')
  drag((s['x'],s['y']), (s['x']-50,s['y']-30),1.25)
  page.keyboard.up('Alt')
  s2=data()['stations'][sid]
  almost(s2['x']+s2['w'],s['x']+s['w'])
  almost(s2['y']+s2['h'],s['y']+s['h'])
  # Go back to a centered view for clicking the two ruler endpoints.
  page.locator('[data-zoom-reset]').click()
  s=data()['stations'][sid]
  page.locator('#panel-close').click()
  page.locator('#dimension-tool-btn').click()
  assert page.locator('#dimension-tool-btn').get_attribute('aria-pressed')=='true'
  click(s['x'],s['y']);click(s['x']+s['w'],s['y'])
  d=data()['dimensions']
  assert len(d)==1,d
  did=next(iter(d));assert d[did]['start_anchor']['id']==sid and d[did]['end_anchor']['id']==sid,d
  assert page.locator('#field-dimension-length').inner_text()==f"{s['w']/100:.2f} m"
  # The dimension tracks station geometry. Edit station directly.
  page.evaluate('window.__dimTest.selectStation('+repr(sid)+')')
  page.locator('#field-station-width').fill('4');page.locator('#field-station-width').dispatch_event('change')
  page.evaluate('window.__dimTest.selectDimension('+repr(did)+')')
  assert page.locator('#field-dimension-length').inner_text()=='4.00 m'
  # Station ID changes and reorder keep ruler references bound to geometry.
  page.evaluate('(sid)=>changeStationId(sid, "11")',sid)
  assert data()['dimensions'][did]['start_anchor']['id']=='11'
  sid='11'
  page.evaluate('window.__dimTest.selectDimension('+repr(did)+')')
  assert page.locator('#field-dimension-length').inner_text()=='4.00 m'
  # Save/load serializes the anchors intact.
  saved=data();page.evaluate('(data)=>window.__builderTest.applyLoadedScenario(data)',saved)
  assert data()['dimensions']==saved['dimensions']
  # Deleting ruler leaves station untouched.
  page.evaluate('window.__dimTest.selectDimension('+repr(did)+')')
  page.locator('#delete-item-btn').click()
  assert not data()['dimensions'] and sid in data()['stations']
  # New line clears dimensions without changing default material boxes.
  page.on('dialog',lambda dialog: dialog.accept())
  page.locator('#new-line-btn').click()
  assert not data()['dimensions'] and len(data()['boxes'])==3
  assert not errors,errors
  browser.close();print('Chromium: four-corner geometry, resize, attached operators, zoom, ruler anchors, physical scale, save/load and deletion passed.')

if __name__=='__main__':check()
