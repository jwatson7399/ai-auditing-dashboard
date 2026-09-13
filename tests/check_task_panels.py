"""Browser regression checks for inline task evidence; no network or production writes."""
import json
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[1]


def main():
    data = json.loads((REPO / 'data/latest.json').read_text())
    data['bench']['gdpval']['historical'] = {'Historical fixture': {'value': 52, 'fetched': '2026-09-03'}}
    # A card with no ranking still has an accessible explanation.
    data['picks']['coding']['rows'] = []
    html = (REPO / 'site/template.html').read_text().replace('/*DATA*/null', json.dumps(data).replace('</', '<\\/'))
    with tempfile.TemporaryDirectory() as folder, sync_playwright() as p:
        file = Path(folder) / 'index.html'
        file.write_text(html)
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route('https://**/*', lambda route: route.abort())
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(file.as_uri())
        cards = page.locator('.task')
        assert cards.count() == 8
        assert page.locator('.evidence-panel:visible').count() == 0

        def placement(index, columns):
            result = page.evaluate('''index => {
              const cards=[...document.querySelectorAll('.task')], card=cards[index];
              const panel=document.getElementById(card.getAttribute('aria-controls'));
              const last=panel.previousElementSibling;
              return {previous:cards.indexOf(last), width:panel.getBoundingClientRect().width,
                gridWidth:document.getElementById('tasks').getBoundingClientRect().width,
                below:panel.getBoundingClientRect().top >= last.getBoundingClientRect().bottom,
                overflow:document.documentElement.scrollWidth > innerWidth};
            }''', index)
            assert result['previous'] == min(7, (index // columns + 1) * columns - 1), result
            assert abs(result['width'] - result['gridWidth']) < 2, result
            assert result['below'] and not result['overflow'], result

        for width, columns in [(1280,4),(981,4),(980,2),(760,2),(521,2),(520,1),(375,1),(320,1)]:
            page.set_viewport_size({'width': width, 'height': 900})
            for index in (0,1,4,7):
                card = cards.nth(index)
                card.focus()
                y = page.evaluate('scrollY')
                card.press('Enter')
                assert page.locator('.evidence-panel:visible').count() == 1
                assert card.get_attribute('aria-expanded') == 'true'
                assert abs(page.evaluate('scrollY') - y) < 2
                assert page.evaluate('location.hash') == ''
                placement(index, columns)
                # Check label geometry, not just the page's overall scroll width.
                for axis in page.locator('.evidence-panel:visible .ticks').all():
                    ticks = axis.evaluate('''el => [...el.children].filter(e=>e.getClientRects().length).map(e=>{
                      const r=e.getBoundingClientRect(); return {text:e.textContent,left:r.left,right:r.right,top:r.top,height:r.height};
                    })''')
                    assert [t['text'] for t in ticks] == (['0','50','100'] if width <= 400 else ['0','25','50','75','100']), ticks
                    assert all(abs(t['top']-ticks[0]['top']) < 1 and t['height'] < 20 for t in ticks), ticks
                    assert all(a['right'] + 2 <= b['left'] for a,b in zip(ticks,ticks[1:])), ticks
                card.press('Space')
                assert card.get_attribute('aria-expanded') == 'false'
                assert page.locator('.evidence-panel:visible').count() == 0
                assert abs(page.evaluate('scrollY') - y) < 2

        # Native Tab order skips every control inside a hidden panel.
        def tab_closed_cards():
            cards.nth(0).focus()
            for index in range(1,8):
                page.keyboard.press('Tab')
                assert cards.nth(index).evaluate('(el)=>el===document.activeElement')
            page.keyboard.press('Tab')
            assert page.evaluate("!document.activeElement.closest('.evidence-panel')")
        tab_closed_cards()

        # Reposition an already open panel across both breakpoints.
        page.set_viewport_size({'width':1280,'height':900})
        cards.nth(1).click()
        panel = page.locator('#evidence-agents')
        panel.locator('details summary').click()
        assert 'Historical fixture: 52, last fetched 2026-09-03' in panel.inner_text()
        def history_not_ranked():
            assert panel.locator('details').get_attribute('open') is not None
            assert 'Historical fixture: 52, last fetched 2026-09-03' in panel.inner_text()
            assert all('Historical fixture' not in text for text in panel.locator('.chart .row').all_text_contents())
        history_not_ranked()
        for width, columns in [(800,2),(375,1),(1280,4)]:
            page.set_viewport_size({'width':width,'height':900})
            page.wait_for_function('''columns => {
              const grid=document.getElementById('tasks'), cards=[...grid.querySelectorAll('.task')];
              return getComputedStyle(grid).gridTemplateColumns.split(' ').length === columns &&
                document.getElementById('evidence-agents').previousElementSibling === cards[Math.floor(1 / columns) * columns + columns - 1];
            }''', arg=columns)
            placement(1, columns)
            history_not_ranked()
        cards.nth(1).focus()
        for index in (2,3):
            page.keyboard.press('Tab')
            assert cards.nth(index).evaluate('(el)=>el===document.activeElement')
        page.keyboard.press('Tab')
        assert panel.locator('.close-evidence').first.evaluate('(el)=>el===document.activeElement')
        page.keyboard.press('Tab')
        assert panel.locator('details summary').evaluate('(el)=>el===document.activeElement')
        page.keyboard.press('Tab')
        assert panel.locator('.close-evidence').last.evaluate('(el)=>el===document.activeElement')
        page.keyboard.press('Tab')
        assert cards.nth(4).evaluate('(el)=>el===document.activeElement')
        # Switching cards closes the old region; Escape restores the trigger's focus.
        cards.nth(2).click()
        assert panel.is_hidden()
        cards.nth(1).click()
        history_not_ranked()
        cards.nth(2).click()
        page.locator('#evidence-frontend .close-evidence').first.focus()
        page.keyboard.press('Escape')
        assert page.locator('.evidence-panel:visible').count() == 0
        assert cards.nth(2).evaluate('(el)=>el===document.activeElement')
        cards.nth(0).click()
        assert 'No models have enough scores' in page.locator('#evidence-coding').inner_text()
        page.locator('#evidence-coding .close-evidence').last.click()
        assert cards.nth(0).evaluate('(el)=>el===document.activeElement')
        tab_closed_cards()
        assert not errors, errors
        browser.close()
    print('Inline evidence checks passed: 8 widths, row placement, keyboard, scroll, resize, history and empty data.')


if __name__ == '__main__':
    main()
