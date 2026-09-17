"""Smart-mode write tool still requires approval; follow strip mirrors the ask."""
from pathlib import Path
import json, os, sys
from playwright.sync_api import sync_playwright
from fixture import glb
ROOT=Path(__file__).resolve().parents[1]
exe=os.environ.get('CHROMIUM_PATH');fails=[]
def check(n,v):
    print(('PASS' if v else 'FAIL'),n)
    if not v:fails.append(n)
def sse(o):return ('data: '+json.dumps(o,ensure_ascii=False)+'\n\n').encode()
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=exe,headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1536,'height':960})
    errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('about:blank#no-auto');pg.set_content((ROOT/'dist/forma_anatomy_studio.html').read_text(),wait_until='load')
    pg.wait_for_function('window.__studio!==undefined')
    pg.route('**/systems/*.glb',lambda r:r.fulfill(status=200,content_type='model/gltf-binary',body=glb(),headers={'Access-Control-Allow-Origin':'*'}))
    pg.locator('[data-action="load-skeleton"]').first.click();pg.wait_for_function('__studio.renderer.objects.length===9')
    pg.locator('[data-tab="agent"]').click();pg.evaluate('__studio.agent.clear()')
    n={'i':0}
    def route(route):
        n['i']+=1
        if n['i']==1:
            body=b''.join([sse({'choices':[{'delta':{'tool_calls':[{'index':0,'id':'a1','type':'function','function':{'name':'focus_structures','arguments':'{"ids":[0]}'}}]}}]}),
                           sse({'choices':[{'finish_reason':'tool_calls'}]}),b'data: [DONE]\n\n'])
            route.fulfill(status=200,content_type='text/event-stream',body=body,headers={'Access-Control-Allow-Origin':'*'})
        else:
            m={'choices':[{'message':{'role':'assistant','content':'已聚焦。'},'finish_reason':'stop'}]}
            route.fulfill(status=200,content_type='application/json',body=json.dumps(m),headers={'Access-Control-Allow-Origin':'*'})
    pg.route('https://agent.example.test/**',route)
    pg.evaluate('''()=>{const c=__studio.agent.config;c.url="https://agent.example.test/v1";c.model="t";c.key="k";c.consent=true;c.permissionMode="smart";}''')
    pg.locator('[data-perm="smart"]').click()
    pg.locator('#chat-input').fill('授权测试');pg.locator('#chat-send').click()
    pg.wait_for_selector('#tool-approval:not([hidden])',timeout=15000)
    asking=pg.evaluate('''()=>{const fs=document.querySelector('#follow-strip');return {stripShown:!fs.hidden, phase:fs.dataset.phase, approveShown:!fs.querySelector('[data-fs=approve]').hidden, denyShown:!fs.querySelector('[data-fs=deny]').hidden};}''')
    check('approval_card_visible',pg.locator('#tool-approval').is_visible())
    check('follow_asking',asking['stripShown'] and asking['phase']=='asking' and asking['approveShown'] and asking['denyShown'])
    pg.locator('[data-agent-approval="approve"]').click()
    pg.wait_for_function('!__studio.agent.busy',timeout=15000)
    pg.wait_for_timeout(1400)
    check('done_after_approve',pg.evaluate('document.querySelector(".answer-slot").textContent.includes("已聚焦")'))
    check('follow_hidden_after',pg.evaluate('document.querySelector("#follow-strip").hidden'))
    check('tool_done_chip',pg.evaluate('!!document.querySelector(".tool-chip:not(.is-error)")'))
    check('no_page_errors',not errs)
    if errs:print('ERRORS',errs[:5])
    b.close()
print('RESULT','ALL_PASS' if not fails else 'FAIL:'+','.join(fails))
sys.exit(1 if fails else 0)
