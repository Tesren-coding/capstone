"""Checks interactive legend and canvas focus without running a Flask server.
Run: python tests/browser_operator_highlight.py
"""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
content=(ROOT/'templates/simulate.html').read_text().split('{% block content %}',1)[1].split('{% endblock %}',1)[0]
HTML='''<!doctype html><html><head><meta charset="utf-8"><style>body{font-family:Arial,sans-serif;} canvas#sim-canvas{width:1000px!important;height:434.17px!important;max-width:none!important;} .canvas-controls{display:flex;gap:8px}</style></head><body data-event-schema-version="1">'''+content+'</body></html>'
SOURCES=['canvas-tools.js','line-direction.js','operator-highlight.js','draw.js','positions.js','state.js','api.js','playback.js']
BUNDLE=''
for filename in SOURCES:
    source=(ROOT/'static/js'/filename).read_text()
    source=re.sub(r'^import\s*\{[\s\S]*?\}\s*from\s*["\'][^"\']+["\'];\s*','',source,flags=re.M)
    source=re.sub(r'\bexport\s+(?=(?:function|class|const|let|async))','',source)
    BUNDLE+='\n'+source+'\n'
BUNDLE+='\nwindow.__highlightTest={getActive:activeHighlightOperator,getVisited:()=>[...highlightedLocations],getRawColor:(x,y)=>[...ctx.getImageData(x,y,1,1).data],getOrdered:()=>[...opNames],view};'
STUB='''() => {window.fetch=async()=>new Response(JSON.stringify({
 event_schema_version:1,takt_time:30,
 scenario:{layout_scale_px_per_m:50,walking_speed_m_per_s:1.2,
 stations:{'1':{x:100,y:190,w:150,h:96,name:'Station A',processes:[{name:'A',manual_time:1,auto_time:0}]},'2':{x:360,y:190,w:150,h:96,name:'Station B',processes:[{name:'B',manual_time:1,auto_time:0}]},'3':{x:620,y:190,w:150,h:96,name:'Station C',processes:[{name:'C',manual_time:1,auto_time:0}]}},
 boxes:{'raw':{x:100,y:380,w:90,h:60,name:'Raw Material',type:'in',start_count:10},
        'swip':{x:360,y:380,w:90,h:60,name:'SWIP',type:'swip',has_part:false},
        'fg':{x:620,y:380,w:90,h:60,name:'Finished',type:'out',capacity:50},
        'direction':{x:100,y:500,w:875,h:85,name:'Arrow',type:'direction'}},
 operators:{'Op10':{x:835,y:170,name:'Tenth Operator',color:[100,150,80],sequence:[{action:'work',loc:'3'}]},
 'Op2':{x:600,y:170,name:'Bob',color:[60,120,220],sequence:[{action:'work',loc:'3'},{action:'drop',loc:'fg'}]},
 'Op1':{x:80,y:170,name:'Alice',color:[220,60,60],attached_to:{station_id:'1',side:'top'},
 sequence:[{action:'pick',loc:'raw'},{action:'work',loc:'2'},{action:'drop',loc:'swip'}]}}},
 events:[{time:1,operator:'Op1',status:'operator_ready'}]
}),{status:200,headers:{'Content-Type':'application/json'}})}'''

def check():
  with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1450,'height':1000}); errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.set_content(HTML);page.evaluate(STUB);page.add_script_tag(content=BUNDLE)
    page.wait_for_selector('[data-operator-id="Op1"]')
    expected_order=['Op1', 'Op2', 'Op10']
    assert page.evaluate('window.__highlightTest.getOrdered()')==expected_order, 'Playback IDs are not numeric-sorted'
    assert page.locator('#operator-highlight-legend button').evaluate_all('(buttons) => buttons.map(b => b.dataset.operatorId)')==expected_order, 'Hover chips not numeric-sorted'
    def focused(): return page.evaluate('window.__highlightTest.getActive()')
    def visited(): return page.evaluate('window.__highlightTest.getVisited()')
    page.wait_for_timeout(70)
    assert focused() is None
    original1=page.evaluate('window.__highlightTest.getRawColor(230,240)')
    original2=page.evaluate('window.__highlightTest.getRawColor(490,240)')
    assert original1[:3]==original2[:3],(original1,original2)
    chip1=page.locator('[data-operator-id="Op1"]')
    chip1.hover(); assert focused()=='Op1',focused()
    assert set(visited())=={'1','2','raw','swip'},visited()
    page.wait_for_timeout(40)
    solid1=page.evaluate('window.__highlightTest.getRawColor(230,240)')
    solid2=page.evaluate('window.__highlightTest.getRawColor(490,240)')
    faded3=page.evaluate('window.__highlightTest.getRawColor(750,240)')
    assert solid1[:3]==solid2[:3], (solid1,solid2)
    assert faded3[3]<solid1[3]-100,(solid1,faded3)
    chip1.click(); assert focused()=='Op1'
    page.mouse.move(1100,50);assert focused()=='Op1','Pinned highlight cleared on hover exit'
    page.locator('[data-operator-id="Op2"]').hover();assert focused()=='Op2'
    assert set(visited())=={'3','fg'}
    page.mouse.move(1100,50); assert focused()=='Op1','Hover did not restore pinned focus'
    page.locator('#clear-operator-highlight').click();page.mouse.move(1100,50)
    assert focused() is None
    canvas=page.locator('#sim-canvas');canvas.scroll_into_view_if_needed()
    bounds=canvas.bounding_box(); assert bounds is not None
    page.mouse.move(bounds['x']+20*bounds['width']/2400,bounds['y']+(1042-30)*bounds['height']/1042)
    assert focused()=='Op1','Canvas legend hover missed'
    page.locator('[data-zoom-in]').click()
    bounds=canvas.bounding_box()
    page.mouse.move(bounds['x']+20*bounds['width']/2400,bounds['y']+(1042-30)*bounds['height']/1042)
    assert focused()=='Op1','Zoom changed canvas legend screen hit location'
    page.mouse.move(1300,70);assert focused() is None
    assert not errors,errors
    print('Chromium operator chips, pinned focus, canvas legend, dimming pixels, and zoom tests passed.')
    browser.close()

if __name__=='__main__':check()
