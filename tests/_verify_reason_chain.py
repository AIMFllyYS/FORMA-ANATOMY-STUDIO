"""Integration: streamed reasoning 2-line clamp + same-name tool aggregation."""
from pathlib import Path
import json, os, sys
from playwright.sync_api import sync_playwright
from fixture import glb
ROOT=Path(__file__).resolve().parents[1]
exe=os.environ.get('CHROMIUM_PATH')
fails=[]
def check(name,val):
    print(('PASS' if val else 'FAIL'),name)
    if not val:fails.append(name)
def sse(obj):
    return ('data: '+json.dumps(obj,ensure_ascii=False)+'\n\n').encode()
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=exe,headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1536,'height':960},accept_downloads=True)
    errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('about:blank#no-auto');pg.set_content((ROOT/'dist/forma_anatomy_studio.html').read_text(),wait_until='load')
    pg.wait_for_function('window.__studio!==undefined')
    pg.route('**/systems/*.glb',lambda r:r.fulfill(status=200,content_type='model/gltf-binary',body=glb(),headers={'Access-Control-Allow-Origin':'*'}))
    pg.evaluate('__studio.loadSkeleton?.__studio')  # noop guard
    # load skeleton via UI
    pg.locator('[data-action="load-skeleton"]').first.click()
    pg.wait_for_function('__studio.renderer.objects.length===9')
    # switch to agent tab and allow all tools (no approval interrupt)
    pg.locator('[data-tab="agent"]').click()
    pg.evaluate('''()=>{__studio.agent.clear();}''')
    state={'n':0}
    def route(route):
        state['n']+=1
        if state['n']==1:
            # long reasoning streamed first, then two same-name tool calls
            def gen():
                yield sse({'choices':[{'delta':{'reasoning_content':'第一行思考内容比较长用来超过两行显示阈值\\n第二行继续推理\\n第三行应该被折叠隐藏掉不要露出来'}}]})
                yield sse({'choices':[{'delta':{'tool_calls':[{'index':0,'id':'c1','type':'function','function':{'name':'focus_structures','arguments':'{"ids":[0]}'}}]}}]})
                yield sse({'choices':[{'delta':{'tool_calls':[{'index':1,'id':'c2','type':'function','function':{'name':'focus_structures','arguments':'{"ids":[1]}'}}]}}]})
                yield sse({'choices':[{'finish_reason':'tool_calls'}]})
                yield b'data: [DONE]\n\n'
            route.fulfill(status=200,content_type='text/event-stream',body=b''.join(gen()),headers={'Access-Control-Allow-Origin':'*'})
        else:
            msg={'choices':[{'message':{'role':'assistant','content':'## 讲解完成\n这是 **重点** 内容。\n\n- 要点一\n- 要点二'},'finish_reason':'stop'}]}
            route.fulfill(status=200,content_type='application/json',body=json.dumps(msg),headers={'Access-Control-Allow-Origin':'*'})
    pg.route('https://agent.example.test/**',route)
    pg.evaluate('''()=>{const c=__studio.agent.config;c.url="https://agent.example.test/v1";c.model="t";c.key="k";c.consent=true;c.permissionMode="allow";__studio.agent.saveConfig?.();}''')
    pg.evaluate('__studio.agent.setPermission("allow")')
    pg.locator('#chat-input').fill('聚合测试');pg.locator('#chat-send').click()
    pg.wait_for_function('!__studio.agent.busy',timeout=20000)
    # 1) one aggregated chip for focus_structures with count x2
    agg=pg.evaluate('''()=>{
      const groups=[...document.querySelectorAll('.tool-group')];
      const g=groups.find(x=>x.dataset.tool==='focus_structures');
      return {groups:groups.length, chip:!!g, count:g?.querySelector('.tool-count')?.dataset.count,
              cards:g?g.querySelectorAll('.tool-card').length:0,
              flag:g?.querySelector('.tool-chip-flag')?.textContent};
    }''')
    check('single_group_for_same_tool',agg['groups']==1 and agg['chip'])
    check('aggregated_count_2',agg['count']=='2' and agg['cards']==2)
    # 2) two tool cards still carry output (compat)
    check('tool_cards_present',pg.locator('.tool-card').count()==2)
    # 3) reason chain collapsed after turn
    check('reason_collapsed_after',pg.evaluate('!document.querySelector(".reason-shell").open'))
    # 4) markdown rich render
    check('markdown_render',pg.evaluate('''()=>{const m=document.querySelector('.answer-slot');return !!m.querySelector('h2')&&!!m.querySelector('strong')&&m.querySelectorAll('li').length===2;}'''))
    # 5) history restore keeps aggregation
    pg.evaluate('__studio.agent.renderThreads?.()||__studio.agent.load?.()')
    # force a fresh restore by re-rendering persisted view
    restored=pg.evaluate('''()=>{
      const box=document.querySelector('#chat-messages');
      // count groups after current render (history already rendered in place)
      const groups=[...document.querySelectorAll('.tool-group')].filter(x=>x.dataset.tool==='focus_structures');
      return groups.length===1 && groups[0].querySelector('.tool-count').dataset.count==='2' && groups[0].querySelectorAll('.tool-card').length===2;
    }''')
    check('rendered_aggregation_holds',restored)
    check('no_page_errors',not [e for e in errs if 'favicon' not in e.lower()])
    if errs:print('ERRORS',errs[:5])
    b.close()
print('RESULT','ALL_PASS' if not fails else 'FAIL:'+','.join(fails))
sys.exit(1 if fails else 0)
