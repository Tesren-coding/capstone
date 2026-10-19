"""Starting SWIP pie dashboard checks, including timeline scrubbing.
Run: python tests/browser_simulation_metrics.py
"""
from playwright.sync_api import sync_playwright
from browser_operator_highlight import HTML, BUNDLE

STUB = '''() => { window.fetch = async () => new Response(JSON.stringify({
  event_schema_version:1, takt_time:30,
  scenario: {
    stations: {
      '1':{x:130,y:240,w:150,h:96,name:'Station 1',has_part:true,processes:[{id:'p1',name:'Proc',manual_time:1,auto_time:0}]},
      '2':{x:350,y:240,w:150,h:96,name:'Station 2',has_part:true,processes:[{id:'p2',name:'Proc',manual_time:1,auto_time:0}]},
      '3':{x:570,y:240,w:150,h:96,name:'Station 3',has_part:false,processes:[{id:'p3',name:'Proc',manual_time:1,auto_time:0}]}
    },
    boxes: {
      'raw':{type:'in',name:'Raw Material',x:120,y:430,w:90,h:60,start_count:10},
      'buffer1':{type:'swip',name:'SWIP 1',x:330,y:430,w:90,h:60,has_part:true},
      'buffer2':{type:'swip',name:'SWIP 2',x:530,y:430,w:90,h:60,has_part:false},
      'out':{type:'out',name:'Finished Goods',x:780,y:430,w:90,h:60,capacity:50},
      'arrow':{type:'direction',name:'Line Direction',x:200,y:80,w:875,h:85}
    },
    operators: {'Op1':{x:200,y:190,name:'Op1',color:[30,70,140],sequence:[]}}
  },
  events: [
    {time:1,status:'pickup',operator:'Op1',loc:'1'},
    {time:2,status:'dropoff',operator:'Op1',loc:'out'},
    {time:3,status:'pickup',operator:'Op1',loc:'buffer1'},
    {time:4,status:'dropoff',operator:'Op1',loc:'buffer2'},
    {time:5,status:'pickup',operator:'Op1',loc:'raw'},
    {time:6,status:'dropoff',operator:'Op1',loc:'1'}
  ]
}),{status:200,headers:{'Content-Type':'application/json'}}); }'''

def check():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1450,'height':1000})
        errors=[]
        page.on('pageerror',lambda error: errors.append(str(error)))
        page.set_content(HTML)
        page.evaluate(STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('#simulation-metrics:visible')
        def total(): return page.locator('#metric-starting-swip').inner_text()
        assert total()=='13' # 2 station parts + one occupied SWIP box + 10 in IN
        assert page.locator('#swip-total-value').text_content()=='13'
        assert page.locator('#swip-pie-legend .swip-legend-value').all_inner_texts()==['2','1','10']
        assert page.locator('#simulation-metrics .sim-metrics-secondary').count()==0
        assert page.locator('#swip-box-summary').count()==0
        for time in (2,5,0):
            page.evaluate(f'seekTo({time})')
            assert total()=='13', 'Starting SWIP changed during playback'
            assert page.locator('#swip-total-value').text_content()=='13'
        assert not errors, errors
        print('Chromium: starting SWIP total/category composition stays fixed during seek/rewind; bottom row removed.')
        browser.close()

if __name__=='__main__':check()
