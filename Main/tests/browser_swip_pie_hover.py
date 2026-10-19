"""Interactive SWIP pie chart and hover tooltips, without starting Flask.
Run: python tests/browser_swip_pie_hover.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_operator_highlight import HTML, BUNDLE
from browser_simulation_metrics import STUB

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT/'static/simulation-dashboard.css').read_text()

def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1450, 'height':1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(HTML)
        page.add_style_tag(content=CSS)
        page.evaluate(STUB)
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('#simulation-metrics:visible')

        # 2 station parts + 1 occupied buffer + 10 starting parts in IN box = 13.
        assert page.locator('#metric-starting-swip').inner_text() == '13'
        assert page.locator('#swip-total-value').text_content() == '13'
        assert page.locator('#swip-box-summary').count() == 0, 'Old permanent caption was not removed'
        assert page.locator('#swip-pie-tooltip:visible').count() == 0
        assert page.locator('.swip-pie-slice').count() == 3
        assert page.locator('#swip-pie-hover-pointer').get_attribute('visibility') == 'hidden'

        # Hover over an individual slice, with pointer and dimming.
        pie = page.locator('.swip-pie-slice[data-key="swipBoxes"]')
        pie.hover(force=True)
        assert page.locator('#swip-pie-tooltip:visible').count() == 1
        assert 'SWIP boxes with parts' in page.locator('#swip-tooltip-title').inner_text()
        assert '1 part · 7.7%' in page.locator('#swip-tooltip-detail').inner_text()
        assert '1 of 2' in page.locator('#swip-tooltip-extra').inner_text()
        assert page.locator('#swip-pie-hover-pointer').get_attribute('visibility') == 'visible'
        assert pie.evaluate('(el) => el.classList.contains("is-hovered")')
        assert page.locator('.swip-pie-slice.is-muted').count() == 2
        assert page.locator('#swip-tooltip-extra').is_visible()

        # Hovering another slice updates the focus and accurate percentage.
        page.locator('.swip-legend-item[data-key="inBoxes"]').hover()
        assert page.locator('#swip-tooltip-title').inner_text() == 'IN boxes starting parts'
        assert '10 parts · 76.9%' in page.locator('#swip-tooltip-detail').inner_text()
        assert page.locator('#swip-tooltip-extra').is_hidden()
        assert page.locator('#swip-tooltip-extra').text_content() == ''
        page.locator('.swip-pie-slice[data-key="stations"]').focus()
        assert page.locator('#swip-tooltip-title').inner_text() == 'Stations with parts'
        assert '2 parts · 15.4%' in page.locator('#swip-tooltip-detail').inner_text()
        assert page.locator('#swip-tooltip-extra').is_hidden()

        # Center shows the total only, without unrelated SWIP box occupancy.
        page.locator('#swip-pie-center').focus()
        assert page.locator('#swip-tooltip-title').inner_text() == 'Total starting SWIP'
        assert page.locator('#swip-tooltip-extra').is_hidden()
        page.locator('#swip-pie-center').blur()
        page.mouse.move(1100, 20)
        assert page.locator('#swip-pie-tooltip:visible').count() == 0

        # Single-category pie must still have visible geometry, not a degenerate arc.
        d = page.evaluate('''() => buildSlicePath(160,160,118,86,-Math.PI/2,3*Math.PI/2)''')
        assert d.count('A ') == 4, d
        assert not errors, errors
        print('Chromium: pie slice hover, leader pointer, legend hover, keyboard focus, SWIP-only occupancy, 100% arc passed.')
        browser.close()

if __name__ == '__main__':
    check()
