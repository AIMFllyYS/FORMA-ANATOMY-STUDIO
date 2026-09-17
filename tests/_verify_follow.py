"""Focused checks for the teaching follow-strip + streaming reason-chain work."""
from pathlib import Path
import json, os, sys
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
exe=os.environ.get('CHROMIUM_PATH')
fails=[]
def check(name,val):
    print(('PASS' if val else 'FAIL'),name)
    if not val:fails.append(name)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=exe,headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1536,'height':960})
    errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('about:blank#no-auto');pg.set_content((ROOT/'dist/forma_anatomy_studio.html').read_text(),wait_until='load')
    pg.wait_for_function('window.__studio!==undefined')
    # module surface
    check('follow_module',pg.evaluate('!!window.FormaFollow && typeof FormaFollow.Follow==="function" && typeof FormaFollow.odometer==="function"'))
    check('follow_dom',pg.evaluate('!!document.querySelector("#follow-strip") && !!document.querySelector("#follow-mirror")'))
    check('timeline_rate',pg.evaluate('(()=>{const t=__studio.timeline;return typeof t.setRate==="function"&&typeof t.cycleRate==="function"&&typeof t.finishNow==="function";})()'))
    # odometer DOM behavior
    odo=pg.evaluate('''()=>{
      const el=document.createElement('span');el.className='odo';el.dataset.count='0';el.textContent='×0';
      FormaFollow.odometer(el,3);
      return {count:el.dataset.count, hasLane:!!el.querySelector('.odo-lane'), next:el.querySelector('.odo-col i:last-child')?.textContent};
    }''')
    check('odometer_count',odo['count']=='3' and odo['hasLane'] and odo['next']=='3')
    # Follow lifecycle: announce -> running -> wait(anim) -> controls/progress -> skip -> done -> hide
    life=pg.evaluate('''async ()=>{
      const f=new FormaFollow.Follow({timeline:()=>__studio.timeline});
      f.lead(0,{zh:'旋转视角',ico:'rotate'},"请看画布");
      f.running({zh:'旋转视角',ico:'rotate'},"z 面");
      await new Promise(r=>setTimeout(r,30));
      const visible=!f.el.hidden, title=f.el.querySelector('.fs-title').textContent;
      f.wait(400,{kind:'hold',ico:'focus',title:'观察 · 聚焦结构',detail:'肱骨'});
      await new Promise(r=>setTimeout(r,30));
      const pauseShown=!f.$('[data-fs=pause]').hidden, skipShown=!f.$('[data-fs=skip]').hidden, rateHidden=f.$('[data-fs=rate]').hidden;
      const mirrorShown=!f.mirror.hidden;
      f.waiter.skip();
      await new Promise(r=>setTimeout(r,30));
      const afterSkip=!f.waiter;
      f.done({zh:'聚焦结构',ico:'focus'},{});
      f.hide();
      const hidden=f.el.hidden && f.mirror.hidden;
      return {visible,title,pauseShown,skipShown,rateHidden,mirrorShown,afterSkip,hidden};
    }''')
    check('follow_lifecycle',all(v for k,v in life.items() if k!='title') and life['title']=='旋转视角中')
    check('no_page_errors',not errs)
    if errs:print('ERRORS:',errs[:5])
    b.close()
print('RESULT', 'ALL_PASS' if not fails else 'FAIL:'+','.join(fails))
sys.exit(1 if fails else 0)
