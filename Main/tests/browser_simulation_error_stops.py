"""Playback stops visibly at a backend blocked event; navigation remains near work areas."""
from playwright.sync_api import sync_playwright
from browser_operator_highlight import HTML, BUNDLE

STUB = '''() => {window.fetch = async () => new Response(JSON.stringify({
 event_schema_version:1,takt_time:2,
 scenario: {layout_scale_px_per_m:50,walking_speed_m_per_s:1.2,
   stations: {'1':{x:200,y:200,w:150,h:96,name:'Bench',has_part:false,processes:[{id:'p1',name:'Test',manual_time:1,auto_time:0}]}},
   boxes: {'in1':{type:'in',name:'Supply',x:20,y:320,w:80,h:60,start_count:0}},
   operators: {'Op1':{x:200,y:150,name:'Op1',color:[40,100,200],sequence:[{action:'work',loc:'1',process:'p1'}]}}},
 events:[{time:0.1,status:'waiting',operator:'Op1',loc:'1',reason:'Waiting for a part'},
         {time:6,status:'blocked',operator:'Op1',loc:'1',reason:'Deadlock / starvation at S1'}]
}),{status:200,headers:{'Content-Type':'application/json'}})}'''

def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1300,'height':900})
        errors=[]
        page.on('pageerror',lambda error: errors.append(str(error)))
        page.set_content(HTML)
        page.evaluate(STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('#timeline:not([disabled])')
        assert page.locator('#operator-highlight-panel #back-btn').count()==1
        assert page.locator('#simulation-error-panel[hidden]').count()==1
        assert '6.00 min' in page.locator('#status-text').inner_text()
        page.evaluate('seekTo(6)')
        assert page.locator('#simulation-error-panel:visible').count()==1
        assert 'Deadlock / starvation at S1' in page.locator('#simulation-error-panel').inner_text()
        assert page.locator('#start-btn').is_disabled()
        assert 'SIMULATION STOPPED' in page.locator('#status-text').inner_text()
        page.locator('#restart-btn').click()
        assert page.locator('#simulation-error-panel[hidden]').count()==1
        assert not page.locator('#start-btn').is_disabled()
        assert not errors, errors
        print('Chromium: simulation error visible, stops playback, restart resets, Back to Builder beside work area.')
        browser.close()

if __name__ == '__main__':check()
