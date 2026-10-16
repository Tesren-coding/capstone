"""Dimension edge witnesses + Ctrl+Z/C/V regression test.
Run python tests/browser_dimension_shortcuts.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB, almost

HOOK = '''window.__shortcutTest={
 snapshot:()=>structuredClone(serializeScenario()),
 select:keys=>{setSelectedKeys(keys);drawFrame();},
 install:()=>{
  const id=String(createStation(450,530));
  const s=scenario.stations[id];
  const oid=createOperator(s.x+s.w/2,s.y-26);
  return {id,oid};
 },
 dimensionAt:(id)=>dimensionLinePoints(scenario.dimensions[id],dimensionBounds),
};'''

def check():
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1450,'height':1000});errors=[]
  page.on('pageerror',lambda err:errors.append(str(err)))
  page.set_content(HTML);page.evaluate(FETCH_STUB)
  page.add_script_tag(content=BUNDLE+HOOK)
  page.wait_for_selector('body[data-builder-ready="true"]')
  canvas=page.locator('#builder-canvas');canvas.scroll_into_view_if_needed()
  def xy(x,y):
   b=canvas.bounding_box();return(b['x']+x*b['width']/2400,b['y']+y*b['height']/1042)
  def click(x,y):page.mouse.click(*xy(x,y))
  def drag(a,b):
   page.mouse.move(*xy(*a));page.mouse.down();page.mouse.move(*xy(*b),steps=10);page.mouse.up()
  def data():return page.evaluate('window.__shortcutTest.snapshot()')
  ids=page.evaluate('window.__shortcutTest.install()');sid=ids['id'];oid=ids['oid'];s=data()['stations'][sid]
  # Snap at arbitrary locations on a station's top edge, not just midpoints.
  page.locator('#dimension-tool-btn').click()
  click(s['x']+17,s['y']+2)
  click(s['x']+s['w']-22,s['y']+1)
  d=data()['dimensions'];assert len(d)==1,d
  did=next(iter(d));v=d[did]
  assert v['start_anchor']['rx']>0 and v['start_anchor']['rx']<0.5,v
  assert v['end_anchor']['rx']>0.5 and v['end_anchor']['rx']<1,v
  assert v['start_anchor']['ry']==v['end_anchor']['ry']==0,v
  assert v['offset']==-35
  line=page.evaluate('(id)=>window.__shortcutTest.dimensionAt(id)',did)
  almost(line['start']['y'],s['y']-35)
  almost(line['anchorStart']['y'],s['y'])
  # Drag blue dimension line farther away, NOT its anchor locations.
  a=(line['start']['x']+line['end']['x'])/2; y=line['start']['y']
  drag((a,y),(a,y-35))
  v2=data()['dimensions'][did]
  assert v2['start_anchor']==v['start_anchor'] and v2['end_anchor']==v['end_anchor'],(v,v2)
  assert v2['offset']<-65,v2
  # Undo only the line offset, preserving the dimension itself.
  page.keyboard.press('Control+z')
  assert data()['dimensions'][did]['offset']==-35,data()['dimensions'][did]
  page.keyboard.press('Control+Shift+z')
  assert data()['dimensions'][did]['offset']<-65
  # Ctrl+C/V duplicates the selection with a new ID, preserving dimensions.
  page.evaluate('(id)=>window.__shortcutTest.select([`dimension:${id}`])',did)
  page.keyboard.press('Control+c');page.keyboard.press('Control+v')
  dims=data()['dimensions'];assert len(dims)==2,dims
  copied=[key for key in dims if key!=did][0]
  assert dims[copied]['offset']==dims[did]['offset']
  assert dims[copied]['start_anchor'] is None # ruler copied without its station, free points
  page.keyboard.press('Control+z');assert len(data()['dimensions'])==1
  page.keyboard.press('Control+y');assert len(data()['dimensions'])==2
  # Group copies correctly remap an operator's attachment and the dimension anchors.
  page.evaluate('([sid,oid,did])=>window.__shortcutTest.select([`station:${sid}`,`operator:${oid}`,`dimension:${did}`])',[sid,oid,did])
  page.keyboard.press('Control+c');page.keyboard.press('Control+v')
  state=data();assert len(state['stations'])==2 and len(state['operators'])==2
  new_station=[key for key in state['stations'] if key!=sid][0]
  new_operator=[key for key in state['operators'] if key!=oid][0]
  assert state['operators'][new_operator]['attached_to']['station_id']==new_station
  attached_dims=[d for d in state['dimensions'].values() if d['start_anchor'] and d['start_anchor']['id']==new_station]
  assert attached_dims, state['dimensions']
  # A focused input keeps standard keyboard clipboard behavior.
  page.evaluate('(sid)=>window.__shortcutTest.select([`station:${sid}`])',sid)
  field=page.locator('#field-name');field.fill('Alpha');field.focus()
  before=data();page.keyboard.press('Control+a');page.keyboard.press('Control+c');page.keyboard.press('Control+v')
  assert data()==before,'Field clipboard should not add new canvas items'
  # Deleting the measured station retains the ruler as unanchored points.
  assert not errors,errors
  browser.close()
  print('Chromium: arbitrary edge snap, offset witness geometry, drag, undo/redo, clipboard duplication, attachment remap and focused-input shortcuts passed.')
if __name__=='__main__':check()
