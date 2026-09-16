"""Local verification of bilingual names, pinyin, and empty-click hide."""
from pathlib import Path
import sys, os
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture import glb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests' / '_runtime'
OUT.mkdir(exist_ok=True)
CHROME = os.environ.get('CHROMIUM_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')

def pos(page, id=0):
    return page.evaluate('''id=>{const r=__studio.renderer,o=__studio.object(id),p=r.project(r.displayPoint(o,o.center)),b=r.canvas.getBoundingClientRect();return{x:p.x+b.left,y:p.y+b.top};}''', id)

fails = []
def check(name, value):
    print(('OK  ' if value else 'FAIL'), name, flush=True)
    if not value:
        fails.append(name)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True, args=['--use-gl=angle', '--use-angle=swiftshader'])
    page = browser.new_page(viewport={'width': 1536, 'height': 960})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('about:blank#no-auto')
    page.set_content((ROOT / 'dist' / 'forma_anatomy_studio.html').read_text(encoding='utf-8'), wait_until='load')
    page.wait_for_function('window.__studio !== undefined')
    page.route('**/systems/*.glb', lambda route: route.fulfill(status=200, content_type='model/gltf-binary', body=glb(), headers={'Access-Control-Allow-Origin': '*'}))
    page.locator('[data-action="load-skeleton"]').filter(visible=True).first.click()
    page.wait_for_function('__studio.renderer.objects.length===9')
    page.wait_for_timeout(250)
    # labels off for GPU pick
    page.locator('[data-action="labels"]').filter(visible=True).first.click()
    pt = pos(page, 0)
    page.mouse.click(pt['x'], pt['y'])
    page.wait_for_timeout(120)
    check('selected', page.evaluate('__studio.state.selected===0'))
    check('pill visible', page.locator('#selection-pill').is_visible())
    check('pill zh', '肱骨' in page.locator('#selection-name').inner_text())
    check('pill en', 'humerus' in page.locator('#selection-en').inner_text().lower())
    check('detail en', 'humerus' in page.locator('#learn-panel .english').inner_text().lower())
    check('detail py', 'gōng' in page.locator('#learn-panel .detail-pinyin').inner_text())
    check('article', '鹰嘴窝' in page.locator('#learn-panel').inner_text())
    page.locator('.detail-subtabs [data-detail="parts"]').click()
    page.wait_for_timeout(80)
    check('landmark py', page.locator('#learn-panel .term-pinyin').count() > 0 and 'gōng' in page.locator('#learn-panel .term-pinyin').first.inner_text())
    page.screenshot(path=str(OUT / 'names_parts.png'))
    page.locator('.detail-subtabs [data-detail="overview"]').click()
    # overlay chinese only
    page.locator('[data-action="labels"]').filter(visible=True).first.click()
    page.wait_for_timeout(80)
    overlay = page.locator('.model-label')
    check('overlay present', overlay.count() > 0)
    if overlay.count():
        t = overlay.first.inner_text()
        check('overlay zh', '肱骨' in t)
        check('overlay no en', 'Humerus' not in t and 'humerus' not in t)
    page.screenshot(path=str(OUT / 'names_selected.png'))
    empty = page.evaluate('''()=>{const r=__studio.renderer,c=r.canvas,b=c.getBoundingClientRect();
      for(let y=b.top+90;y<b.bottom-140;y+=20){
        for(let x=b.left+90;x<b.right-90;x+=20){
          if(document.elementFromPoint(x,y)!==c)continue;
          if(!r.pick(x,y))return{x,y};
        }
      }return null;}''')
    check('empty target', empty is not None)
    if empty:
        page.mouse.click(empty['x'], empty['y'])
        page.wait_for_timeout(120)
    check('pill hidden', page.locator('#selection-pill').is_hidden())
    check('overlay hidden', page.locator('.model-label').count() == 0)
    check('still selected', page.evaluate('__studio.state.selected===0 && __studio.state.nameHint===false'))
    check('detail remains', '鹰嘴窝' in page.locator('#learn-panel').inner_text())
    page.screenshot(path=str(OUT / 'names_hidden.png'))
    check('no pageerror', errors == [])
    if errors:
        print('ERRORS', errors)
    browser.close()

print('FAILED' if fails else 'ALL PASSED', fails)
sys.exit(1 if fails else 0)
