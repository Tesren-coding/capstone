"""Test four dock edges, collapse/reopen and persistent placement."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'templates/builder.html').read_text()
css = source.split('{% block styles %}<style>',1)[1].split('</style>',1)[0]
content = source.split('{% block content %}',1)[1].split('{% endblock %}',1)[0]
html = ('<!doctype html><html><head><style>body{font:14px Arial} main{max-width:1000px;margin:auto}'
        '#builder-canvas{width:1000px;height:434px;max-width:none!important}.builder-canvas-shell{width:1000px}'
        '</style><style>'+css+'</style></head><body><main>'+content+'</main></body></html>')
js = (ROOT/'static/js/line-tool-dock.js').read_text()
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1450,'height':960})
    page.set_content(html)
    page.add_script_tag(content=js)
    panel = page.locator('#line-tool-panel')
    handle = page.locator('#line-tool-handle')
    shell = page.locator('#builder-canvas-shell')
    assert panel.get_attribute('data-dock') == 'left'
    for edge in ('right','top','bottom','left'):
        sb = shell.bounding_box()
        positions = {'right':(sb['x']+sb['width']-15,sb['y']+sb['height']/2),
                     'left':(sb['x']+15,sb['y']+sb['height']/2),
                     'top':(sb['x']+sb['width']/2,sb['y']+15),
                     'bottom':(sb['x']+sb['width']/2,sb['y']+sb['height']-15)}
        hb=handle.bounding_box()
        page.mouse.move(hb['x']+20,hb['y']+15)
        page.mouse.down()
        page.mouse.move(*positions[edge],steps=12)
        page.mouse.up()
        assert panel.get_attribute('data-dock')==edge,(edge,panel.get_attribute('data-dock'))
        direction=page.locator('#toolbar').evaluate('(el)=>getComputedStyle(el).flexDirection')
        assert direction == ('row' if edge in ('top','bottom') else 'column'), (edge,direction)
    page.locator('#line-tool-collapse').click()
    assert 'collapsed' in panel.get_attribute('class')
    page.locator('#line-tool-collapse').click()
    assert 'collapsed' not in panel.get_attribute('class')
    assert page.locator('#toolbar .add-btn').count()==6
    assert page.locator('#builder-under-canvas #run-scenario-btn').count()==1
    assert page.locator('#builder-under-canvas #takt-time-input').count()==1
    assert page.locator('#open-device-file-btn').is_visible()
    assert page.locator('#save-scenario-btn').is_visible()
    browser.close()
print('Line Tool docking, layout orientation, hide/show and tool placements passed.')
