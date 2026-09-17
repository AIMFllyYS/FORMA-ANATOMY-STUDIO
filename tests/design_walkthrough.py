# -*- coding: utf-8 -*-
"""Task 23 design walkthrough: light/dark/narrow screenshots of v4 surfaces.

SYNTHETIC GRAPHICS NOT ANATOMY: fixture mesh is a sphere; node names only
drive nomenclature grouping. Screenshots land in tests/_runtime/walk/.
"""
from pathlib import Path
import sys, os
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture import glb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests' / '_runtime' / 'walk'
OUT.mkdir(parents=True, exist_ok=True)
CHROME = os.environ.get('CHROMIUM_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')

fails = []
def check(name, value):
    print(('OK  ' if value else 'FAIL'), name, flush=True)
    if not value:
        fails.append(name)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True,
        args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])

    def new_page(width=1536, height=960, dark=False):
        ctx = browser.new_context(viewport={'width': width, 'height': height},
            color_scheme='dark' if dark else 'light')
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto('about:blank#no-auto')
        page.set_content((ROOT / 'dist' / 'forma_anatomy_studio.html').read_text(encoding='utf-8'), wait_until='load')
        page.wait_for_function('window.__studio !== undefined')
        page.route('**/systems/*.glb', lambda route: route.fulfill(status=200,
            content_type='model/gltf-binary', body=glb(),
            headers={'Access-Control-Allow-Origin': '*'}))
        return page, ctx, errors

    def load_synth(page):
        page.locator('[data-action="load-skeleton"]').filter(visible=True).first.click()
        page.wait_for_function('__studio.renderer.objects.length===9')
        page.wait_for_timeout(200)

    def open_action(page, name):
        page.click('[data-action="menu"]')
        page.wait_for_timeout(150)
        page.locator(f'#popover [data-action="{name}"]').first.dispatch_event('click')
        page.wait_for_timeout(300)

    # ---------- Desktop light ----------
    page, ctx, errors = new_page(dark=False)
    load_synth(page)
    check('light: functional group labels present', page.evaluate(
        "!!document.querySelector('.tree-group,[data-group]') || document.body.innerText.includes('自由') || document.body.innerText.includes('上肢')"))
    # open settings center
    open_action(page, 'agent-settings')
    check('light: settings modal opens', page.evaluate("!!document.querySelector('.modal,[role=dialog]') && document.body.innerText.includes('设置')"))
    page.screenshot(path=str(OUT / '01_light_settings.png'))
    # close modal
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    # resources modal with tiers
    open_action(page, 'resources')
    body = page.evaluate('document.body.innerText')
    check('light: tiers standard/balanced/HD shown', all(k in body for k in ('standard', 'balanced', 'HD')))
    page.screenshot(path=str(OUT / '02_light_resources_tiers.png'))
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    # select first object -> detail badge + latin
    page.evaluate("""() => { const o=__studio.renderer.objects.find(x=>/__humerus/i.test(x.name||'')); if(o){__studio.select(o);} }""")
    page.wait_for_timeout(250)
    detail = page.evaluate('document.body.innerText')
    check('light: trust badge text present', ('审校' in detail) or ('未规范' in detail) or ('待审' in detail))
    page.screenshot(path=str(OUT / '03_light_detail_badge.png'))
    ctx.close()

    # ---------- Desktop dark ----------
    page, ctx, errors = new_page(dark=False)
    load_synth(page)
    # app theme is manual (not system-driven); switch explicitly
    page.evaluate("__studio && document.documentElement.dataset.theme==='light' ? document.querySelector('[data-action=theme]').click() : null")
    page.wait_for_timeout(200)
    check('dark: theme applied', page.evaluate("document.documentElement.dataset.theme==='dark'"))
    open_action(page, 'resources')
    page.screenshot(path=str(OUT / '04_dark_resources.png'))
    check('dark: no page errors', not errors)
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    open_action(page, 'agent-settings')
    page.screenshot(path=str(OUT / '05_dark_settings.png'))
    check('dark: settings rendered', page.evaluate("document.body.innerText.includes('设置')"))
    ctx.close()

    # ---------- Narrow / mobile ----------
    page, ctx, errors = new_page(width=390, height=844)
    load_synth(page)
    overflow_x = page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth + 1')
    check('narrow: no horizontal overflow', not overflow_x)
    open_action(page, 'agent-settings')
    modal_overflow = page.evaluate("""() => { const m=document.querySelector('.modal,[role=dialog]'); if(!m) return true; return m.scrollWidth<=m.clientWidth+2; }""")
    check('narrow: settings fits modal', modal_overflow)
    page.screenshot(path=str(OUT / '06_narrow_settings.png'), full_page=False)
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    open_action(page, 'resources')
    page.screenshot(path=str(OUT / '07_narrow_resources.png'), full_page=False)
    check('narrow: no page errors', not errors)
    ctx.close()

    print('SHOTS', sorted(p.name for p in OUT.glob('*.png')))
    print('ALL PASSED' if not fails else 'FAILS', fails)
    sys.exit(1 if fails else 0)
