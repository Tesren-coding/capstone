"""Playback scrubber stays immediately beneath the simulator canvas.
Run: python tests/browser_timeline_below_canvas.py
"""
from playwright.sync_api import sync_playwright
from browser_simulation_metrics import STUB
from browser_operator_highlight import HTML, BUNDLE, ROOT


def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1450, 'height': 1000})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.set_content(HTML)
        # Exercise the actual simulation stylesheet, not only the DOM order.
        page.add_style_tag(content=(ROOT / 'static' / 'simulation-dashboard.css').read_text() +
                           '#sim-canvas{width:100%!important;height:auto!important;max-width:100%!important;}')
        page.evaluate(STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('#simulation-metrics:visible')
        assert page.locator('#timeline').count() == 1
        assert page.locator('#sim-canvas + .simulation-playback-timeline #timeline').count() == 1
        canvas_box = page.locator('#sim-canvas').bounding_box()
        slider_box = page.locator('#timeline').bounding_box()
        assert slider_box['y'] >= canvas_box['y'] + canvas_box['height'], (canvas_box, slider_box)
        assert page.locator('.simulation-canvas-and-timeline > #sim-canvas').count() == 1
        assert page.evaluate("document.querySelector('#timeline').compareDocumentPosition(document.querySelector('#sim-canvas')) & Node.DOCUMENT_POSITION_PRECEDING")
        assert not page.locator('#timeline').is_disabled()
        page.locator('#timeline').evaluate("el => { el.value = '3'; el.dispatchEvent(new Event('input', {bubbles: true})); }")
        assert page.locator('#timeline-label').inner_text() == '3.00 / 6.00 min'
        assert not errors, errors
        browser.close()
        print('Chromium: timeline directly below canvas, enabled, and seeks simulation.')


if __name__ == '__main__':
    check()
