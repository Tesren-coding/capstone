"""Browser interaction check using the real builder.js and a local fetch mock.

Run `python tests/browser_builder_smoke.py` with Playwright and Chromium.
The JavaScript modules run inline, because browser navigation is blocked in
some sandbox environments. Server validation is separately tested in Python.
"""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
content = (ROOT/'templates/builder.html').read_text().split('{% block content %}',1)[1].split('{% endblock %}',1)[0]
HTML = ('''<!doctype html><html><head><meta charset="utf-8">
<style>body{font-family:Arial,sans-serif;} canvas#builder-canvas{
width:1000px!important;height:434.17px!important;max-width:none!important;}
.canvas-controls{display:flex;gap:8px}.card{padding:8px}#toolbar,#toolbar2{margin:4px 0!important}</style>
</head><body data-scenario-schema-version="2">'''+content+'''</body></html>''')

# Inline the actual source modules for testing on an about:blank document;
# this environment blocks Chromium navigation, including localhost.
SOURCES = ['canvas-tools.js','drag-sort.js','api.js','layout-geometry.js',
           'builder-snapping.js','line-direction.js','builder.js']
BUNDLE = ''
for filename in SOURCES:
    js=(ROOT/'static/js'/filename).read_text()
    js=re.sub(r'^import\s*\{[\s\S]*?\}\s*from\s*[\"\'][^\"\']+[\"\'];\s*', '', js, flags=re.M)
    js=re.sub(r'\bexport\s+(?=(?:function|class|const|let|async))', '', js)
    BUNDLE+='\n'+js+'\n'
BUNDLE+='\nwindow.__builderTest={serializeScenario,applyLoadedScenario,changeStationId,reorderStations,view};'

FETCH_STUB = r'''() => {
 const store={};
 Object.defineProperty(window,'sessionStorage',{configurable:true,value:{
   getItem:k=>store[k]??null,setItem:(k,v)=>{store[k]=v},removeItem:k=>{delete store[k]}
 }});
 window.__savedByTest={};
 window.fetch=async(url,options={})=>{
   const payload=options.body?JSON.parse(options.body):{};
   let result={};
   if(url==='/import-scenario') result={scenario:payload.scenario,status:'imported'};
   if(url==='/export-scenario') result=payload.scenario;
   if(url==='/list-scenarios') result={files:Object.keys(window.__savedByTest)};
   if(url==='/save-scenario'){
     const filename=payload.filename||(payload.name.trim().replace(/[^A-Za-z0-9_\- ]/g,'').replace(/ /g,'_')+'.json');
     window.__savedByTest[filename]=payload.scenario;
     result={status:'saved',filename,revision:'r1'};
   }
   if(url.startsWith('/load-scenario/')){
     const filename=decodeURIComponent(url.split('/').pop());
     result={found:!!window.__savedByTest[filename],filename,revision:'r1',scenario:window.__savedByTest[filename]};
   }
   if(url==='/rename-scenario'){
     const original=payload.filename;
     const filename=payload.new_name.trim().replace(/[^A-Za-z0-9_\- ]/g,'').replace(/ /g,'_').replace(/\.json$/i,'')+'.json';
     if(!window.__savedByTest[original]) result={status:'missing',error:'Original not found.'};
     else if(original!==filename && window.__savedByTest[filename]) result={status:'exists',error:'A scenario with the new name already exists.'};
     else {
       window.__savedByTest[filename]=window.__savedByTest[original];
       if(original!==filename) delete window.__savedByTest[original];
       result={status:'renamed',filename,revision:'r1'};
     }
   }
   return new Response(JSON.stringify(result),{status:200,headers:{'Content-Type':'application/json'}});
 };
} '''

def almost(a,b):
    assert abs(a-b)<1.5, (a,b)

def check():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
        errors=[]
        page.on('pageerror',lambda exc:errors.append(str(exc)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')
        canvas=page.locator('#builder-canvas')
        canvas.scroll_into_view_if_needed()

        def mouse_at(x,y,scale=1):
            # Canvas world -> canvas pixels -> displayed CSS pixels.
            left=1200*(1-scale);top=521*(1-scale)
            box=canvas.bounding_box()
            assert box is not None
            return (box['x'] + (x*scale+left)*box['width']/2400,
                    box['y'] + (y*scale+top)*box['height']/1042)
        def click_world(x,y,scale=1): page.mouse.click(*mouse_at(x,y,scale))
        def drag_world(x1,y1,x2,y2,scale=1):
            page.mouse.move(*mouse_at(x1,y1,scale))
            page.mouse.down(); page.mouse.move(*mouse_at(x2,y2,scale),steps=7); page.mouse.up()
        def put(kind,x,y,scale=1):
            page.locator(f'.add-btn[data-type="{kind}"]').click()
            canvas.scroll_into_view_if_needed()
            click_world(x,y,scale)
        def export():
            return page.evaluate('window.__builderTest.serializeScenario()')

        put('station',400,320)
        put('station',570,320)
        data=export()
        almost(data['stations']['1']['x'],325)
        almost(data['stations']['2']['x'],497)
        for station in data['stations'].values():
            assert (station['w'],station['h'])==(150,96)
        assert data['stations']['2']['y']==data['stations']['1']['y']
        put('operator',402,246)
        data=export();op=data['operators']['Op1']
        assert op['attached_to']=={'station_id':'1','side':'top'},op
        almost(op['y']+16+10,data['stations']['1']['y'])

        # Drag a station; the attached operator tracks its new anchor.
        drag_world(360,305,460,605)
        data=export();s=data['stations']['1'];op=data['operators']['Op1']
        almost(s['x'],425);almost(s['y'],572)
        almost(op['x'],s['x']+75);almost(op['y'],s['y']-26)

        # Move the operator directly into the lower slot of station 2.
        drag_world(op['x'],op['y'],572,394)
        data=export();op=data['operators']['Op1']
        assert op['attached_to']=={'station_id':'2','side':'bottom'},op

        # Renumber S2 to S3: its operator anchor remaps with it.
        click_world(525,305)
        page.locator('#field-station-id').fill('3')
        page.locator('#station-id-apply').click()
        data=export()
        assert '3' in data['stations'] and '2' not in data['stations'],data['stations']
        assert data['operators']['Op1']['attached_to']['station_id']=='3'

        # Reorder IDs: attachment follows the physical station, then maps
        # back after restoring the original station order.
        page.evaluate('window.__builderTest.reorderStations("3", "1")')
        data=export()
        assert data['operators']['Op1']['attached_to']['station_id']=='1'
        almost(data['stations']['1']['x'],497)
        page.evaluate('window.__builderTest.reorderStations("1", null)')
        data=export()
        assert data['operators']['Op1']['attached_to']['station_id']=='3'
        almost(data['stations']['1']['x'],425)

        # Verify operator slot placement under zoom, with transformed pointer coordinates.
        page.locator('[data-zoom-in]').click()
        assert page.locator('[data-zoom-label]').inner_text()=='125%'
        # Check station insertion and station dragging while zoomed to 125%.
        put('station',746,321,1.25)
        data=export()
        almost(data['stations']['4']['x'],669)
        almost(data['stations']['4']['y'],data['stations']['3']['y'])
        drag_world(700,305,1000,505,1.25)
        data=export()
        almost(data['stations']['4']['x'],969)
        almost(data['stations']['4']['y'],data['stations']['3']['y']+200)

        # Station 1 at 425,572, its left slot is (399,620).
        put('operator',401,619,1.25)
        data=export()
        assert data['operators']['Op2']['attached_to']=={'station_id':'1','side':'left'},data['operators']['Op2']

        # Drag the attached operator away at 125%: detaches; other operator unchanged.
        op=data['operators']['Op2'];drag_world(op['x'],op['y'],op['x']+115,op['y']+120,1.25)
        data=export()
        assert 'attached_to' not in data['operators']['Op2'],data['operators']['Op2']
        assert data['operators']['Op1']['attached_to']['station_id']=='3'
        almost(data['operators']['Op2']['x'],399+115)

        # Real save route, then browser reload: session draft returns via import API.
        page.on('dialog',lambda dialog:dialog.accept('smoke-line'))
        page.locator('#save-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Saved")')
        saved=page.evaluate('window.__savedByTest["smoke-line.json"]')
        page.evaluate('window.__builderTest.applyLoadedScenario(window.__savedByTest["smoke-line.json"])')
        data=export();assert data==saved,'Scenario load changed coordinates/attachments'

        # Delete station 3 and leave operator at its last absolute position.
        page.locator('[data-zoom-reset]').click()
        click_world(530,300)
        page.locator('#delete-item-btn').click()
        data=export()
        assert '3' not in data['stations']
        assert 'attached_to' not in data['operators']['Op1'],data['operators']['Op1']
        assert not errors,errors
        print('Chromium: placement, drag, 125% zoom, renumber/reorder, save/load, delete-detach passed.')
        browser.close()

if __name__=='__main__': check()
