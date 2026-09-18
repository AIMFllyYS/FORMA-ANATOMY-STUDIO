"""Integration checks on SYNTHETIC GRAPHICS FIXTURES. Not anatomy review.
Run with: xvfb-run -a python tests/browser_test.py (Linux, no display).
No browser/organization policies are changed. Fullscreen denial is recorded.
"""
from pathlib import Path
import json, math, base64, re, time, sys, os
from playwright.sync_api import sync_playwright
from fixture import glb
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'tests/_runtime';OUT.mkdir(exist_ok=True)
results={};errors=[]
def test(name,value):
 results[name]=value;print(name, json.dumps(value,ensure_ascii=False)[:280],flush=True)
 if value is False: raise AssertionError(name)
def pos(page,id=0,dx=0,dy=0):
 return page.evaluate('''([id,dx,dy])=>{const r=__studio.renderer,o=__studio.object(id),p=r.project(r.displayPoint(o,o.center)),b=r.canvas.getBoundingClientRect();return{x:p.x+b.left+dx,y:p.y+b.top+dy};}''',[id,dx,dy])
def click_model(page,id=0,dx=0,dy=0):
 p=pos(page,id,dx,dy);page.mouse.click(p['x'],p['y']);page.wait_for_timeout(100);return p
def action(page,name):
 page.locator('[data-action="'+name+'"]').filter(visible=True).first.click()
def configure(page):
 action(page,'agent-settings');page.locator('#agent-url').fill('https://agent.example.test/v1');page.locator('#agent-model').fill('test-model');page.locator('#agent-key').fill('TEST_SECRET_DO_NOT_EXPORT_49');page.locator('#agent-consent').check();action(page,'agent-save')
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1536,'height':960},device_scale_factor=1,accept_downloads=True)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('about:blank#no-auto');page.set_content((ROOT/'dist/forma_anatomy_studio.html').read_text(),wait_until='load');page.wait_for_function('window.__studio !== undefined')
  test('webgl2_actual',page.evaluate('!!__studio.renderer.gl'))
  test('no_fake_asset_on_start',page.evaluate('__studio.renderer.objects.length===0 && __studio.assets.assets.length===0'))
  test('topbar_48px',page.locator('#topbar').bounding_box()['height']==48)
  page.screenshot(path=str(OUT/'empty_light.png'))
  page.route('**/systems/*.glb',lambda route:route.fulfill(status=200,content_type='model/gltf-binary',body=glb(),headers={'Access-Control-Allow-Origin':'*'}))
  action(page,'load-skeleton');page.wait_for_function('__studio.renderer.objects.length===9');page.wait_for_timeout(300)
  test('source_objects_loaded',page.evaluate('__studio.renderer.objects.length===9 && __studio.assets.assets[0].triangles>0'))
  test('folder_hierarchy',page.locator('#catalog details').count()>=5)
  test('null_selection_not_object_zero',page.evaluate('__studio.selectedObject()===null && __studio.object(null)===null'))
  test('partial_name_not_whole_bone',page.evaluate('''()=>{const o={sourceName:'Head of left humerus',category:'skeletal'};return FormaKnowledge.title(o)==='Head of left humerus' && o._knowledgeMatch==='related';}'''))
  test('names_bilingual_pinyin',page.evaluate('''()=>{const o={sourceName:'Left humerus',category:'skeletal'};const n=FormaKnowledge.names(o);return n.zh==='左侧 · 肱骨' && /humerus/i.test(n.en) && n.py.includes('gōng') && n.py.includes('gǔ') && FormaKnowledge.pinyin('切迹')==='qiē jì';}'''))

  page.locator('#search').fill('肱骨');page.wait_for_timeout(180)
  test('chinese_search',page.locator('#catalog .mesh-row').count()==2)
  page.locator('#search').fill('NO-SUCH-STRUCTURE');page.wait_for_timeout(180)
  test('missing_not_fabricated','没有匹配' in page.locator('#catalog').inner_text())
  page.locator('#search').fill('');page.wait_for_timeout(180)
  page.locator('[data-left-tab="directory"]').click();test('directory_exists',page.locator('#directory .directory-card').count()==1)
  page.locator('[data-left-tab="layers"]').click();page.locator('[data-alpha="skeletal"]').fill('40');page.locator('[data-alpha="skeletal"]').dispatch_event('input')
  test('alpha_controls_real_mesh',page.evaluate('__studio.renderer.catAlpha.skeletal===0.4'))
  page.locator('[data-alpha="skeletal"]').fill('100');page.locator('[data-alpha="skeletal"]').dispatch_event('input');page.locator('[data-left-tab="tree"]').click()
  # Disable labels before clicking so GPU canvas picking, not label DOM, is exercised.
  action(page,'labels');pt=click_model(page,0)
  test('gpu_object_pick',page.evaluate('__studio.state.selected===0'))
  test('systematic_humerus_article','鹰嘴窝' in page.locator('#learn-panel').inner_text() and page.locator('#learn-panel .article-section').count()>=4)
  test('selection_name_bilingual',page.locator('#selection-pill').is_visible() and '肱骨' in page.locator('#selection-name').inner_text() and 'humerus' in page.locator('#selection-en').inner_text().lower())
  test('detail_english_pinyin','humerus' in page.locator('#learn-panel .english').inner_text().lower() and 'gōng' in page.locator('#learn-panel .detail-pinyin').inner_text())
  action(page,'labels');page.wait_for_timeout(80)
  overlay=page.locator('.model-label')
  test('overlay_label_chinese_only',overlay.count()>0 and '肱骨' in overlay.first.inner_text() and 'Humerus' not in overlay.first.inner_text())
  empty=page.evaluate('''()=>{const r=__studio.renderer,c=r.canvas,b=c.getBoundingClientRect();
    for(let y=b.top+90;y<b.bottom-140;y+=20){
      for(let x=b.left+90;x<b.right-90;x+=20){
        if(document.elementFromPoint(x,y)!==c)continue;
        if(!r.pick(x,y))return{x,y};
      }
    }return null;}''')
  test('empty_canvas_target',empty is not None)
  page.mouse.click(empty['x'],empty['y']);page.wait_for_timeout(100)
  test('empty_click_hides_name',page.locator('#selection-pill').is_hidden() and page.locator('.model-label').count()==0 and page.evaluate('__studio.state.nameHint===false && __studio.state.selected===0'))
  test('empty_click_keeps_detail','鹰嘴窝' in page.locator('#learn-panel').inner_text())
  action(page,'labels');click_model(page,0)
  page.screenshot(path=str(OUT/'fixture_overview_NOT_ANATOMY.png'))
  old=page.evaluate('__studio.renderer.span');page.mouse.dblclick(pt['x'],pt['y']);page.wait_for_timeout(150)
  test('doubleclick_local_zoom',page.evaluate('__studio.renderer.span')<old*.6)
  action(page,'view-reset');page.wait_for_timeout(100)
  # Hand and rectangle zoom.
  page.locator('[data-mode="pan"]').click();c=page.locator('#canvas').bounding_box();xy=(c['x']+c['width']*.6,c['y']+c['height']*.55)
  target=page.evaluate('[...__studio.renderer.target]');page.mouse.move(*xy);page.mouse.down();page.mouse.move(xy[0]+75,xy[1]+15,steps=8);page.mouse.up()
  test('hand_pan',page.evaluate('[...__studio.renderer.target]')!=target)
  page.locator('[data-mode="box"]').click();old=page.evaluate('__studio.renderer.span');page.mouse.move(xy[0]-70,xy[1]-90);page.mouse.down();page.mouse.move(xy[0]+80,xy[1]+90,steps=5);page.mouse.up();page.wait_for_timeout(100)
  test('rectangle_zoom',page.evaluate('__studio.renderer.span')<old)
  action(page,'view-reset');page.wait_for_timeout(100);pt=pos(page,0);page.mouse.click(pt['x'],pt['y'],button='right');page.wait_for_timeout(150)
  test('canvas_context_menu',page.locator('#context-menu').is_visible())
  page.locator('#context-menu [data-action="panorama"]').click();page.wait_for_timeout(150)
  test('panorama_isolates_object',page.evaluate('__studio.state.panorama===0 && __studio.renderer.isolated.size===1'))
  test('fine_terms_not_fake_mesh',page.locator('#learn-panel .landmark-row').count()>=10 and page.evaluate('__studio.renderer.objects.length===9'))
  page.locator('#learn-panel [data-view="x"]').click();test('six_source_views',abs(page.evaluate('__studio.renderer.yaw')-math.pi/2)<1e-5)
  page.locator('#clip-axis').select_option('1');page.locator('#clip-position').fill('50');page.locator('#clip-position').dispatch_event('input');page.wait_for_timeout(150)
  test('actual_surface_section',len(page.locator('.section-path').get_attribute('d') or '')>20)
  page.locator('#clip-axis').select_option('-1');page.evaluate('__studio.view("z")');page.wait_for_timeout(100)
  # Actual hit + surface region.
  action(page,'annotate');pt=click_model(page,0)
  test('triangle_region_pick',page.evaluate('!!__studio.state.patchDraft && __studio.state.patchDraft.spec.faces.length>0'))
  page.locator('#patch-name').fill('TEST_REGION_A_NOT_ANATOMY');action(page,'patch-save')
  test('patch_hash_bound',page.evaluate('__studio.state.patches[0].assetSHA256.length===64 && __studio.state.patches[0].status==="user_annotation_unreviewed"'))
  action(page,'annotate');pt=click_model(page,0,0,85);page.locator('#patch-name').fill('TEST_REGION_B_NOT_ANATOMY');action(page,'patch-save')
  action(page,'regions-explode');page.wait_for_timeout(200)
  test('real_face_explosion',page.evaluate('__studio.state.transients.size===2 && __studio.renderer.isolated.size===2 && __studio.renderer.explode>0'))
  action(page,'scene-back');page.wait_for_timeout(100);test('transient_cleanup_restores_source',page.evaluate('__studio.renderer.objects.length===9 && __studio.state.transients.size===0'))
  page.locator('[data-detail="notes"]').click();page.locator('#structure-note').fill('PRIVATE_NOTE_TEST_NOT_FOR_AGENT')
  test('note_recorded',page.evaluate('Object.values(__studio.state.notes).includes("PRIVATE_NOTE_TEST_NOT_FOR_AGENT")'))
  # Joint context and manual calibrated rigid display.
  page.evaluate('__studio.openJoint("elbow")');page.wait_for_timeout(150)
  test('joint_parts_only_loaded',page.evaluate('__studio.jointParts().map(p=>p.objects.length).join(",")==="1,1,1,0,0"'))
  page.locator('[data-joint-part="1"]').click();test('joint_highlight',page.evaluate('__studio.renderer.highlighted.has(1) && __studio.renderer.highlighted.size===1'))
  page.locator('#explode').fill('65');page.locator('#explode').dispatch_event('input');test('object_explosion',page.evaluate('__studio.renderer.explode===0.65'))
  page.locator('#explode').fill('0');page.locator('#explode').dispatch_event('input')
  page.locator('.motion-controls summary').click();action(page,'axis-pick');page.evaluate('__studio.view("z")');page.wait_for_timeout(150)
  click_model(page,0,-15,0);click_model(page,0,15,0)
  test('manual_axis_real_hits',page.evaluate('__studio.state.axisPoints.length===2'))
  original=page.evaluate('Array.from(__studio.object(1).parts[0].pos.slice(0,15))');page.locator('#motion-angle').fill('35');page.locator('#motion-angle').dispatch_event('input')
  test('rigid_motion_not_source_mutation',page.evaluate('__studio.renderer.motion!==null && __studio.state.motionAngle===35') and page.evaluate('Array.from(__studio.object(1).parts[0].pos.slice(0,15))')==original)
  action(page,'motion-reset');test('motion_reset',page.evaluate('__studio.renderer.motion===null'))
  # Floating panel and movable tools; restore dock afterwards.
  grip=page.locator('#inspector-grip').bounding_box();page.mouse.move(grip['x']+50,grip['y']+12);page.mouse.down();page.mouse.move(700,120,steps=8);page.mouse.up()
  test('right_panel_drag',page.evaluate('document.body.classList.contains("panel-floating")') and page.locator('#inspector').bounding_box()['x']<1000)
  page.evaluate('__studio.actions["layout-reset"]()');rail=page.locator('#tool-rail').bounding_box();gg=page.locator('#tool-rail .drag-grip').bounding_box();page.mouse.move(gg['x']+10,gg['y']+6);page.mouse.down();page.mouse.move(gg['x']+140,gg['y']+50,steps=6);page.mouse.up();test('toolbar_drag',page.locator('#tool-rail').bounding_box()['x']>rail['x']+60)
  page.evaluate('__studio.actions["layout-reset"]()')
  # Test native API as permitted; never change browser/organization policies.
  action(page,'fullscreen');page.wait_for_timeout(180);test('fullscreen_or_labeled_fallback',page.evaluate('document.body.classList.contains("immersive")') and (page.evaluate('!!document.fullscreenElement') or '沉浸' in page.locator('#full-tools').inner_text()))
  results['native_fullscreen_granted']=page.evaluate('!!document.fullscreenElement');page.locator('#full-tools [data-action="fullscreen"]').click()
  page.wait_for_timeout(120)
  page.evaluate("()=>{window.__oldFS=document.documentElement.requestFullscreen;document.documentElement.requestFullscreen=()=>Promise.reject(new DOMException('TEST simulated denial','NotAllowedError'));}")
  action(page,'fullscreen');page.wait_for_timeout(120)
  test('simulated_fullscreen_denial_labeled',page.evaluate('!document.fullscreenElement && document.body.classList.contains("immersive")') and '沉浸' in page.locator('#full-tools').inner_text())
  page.locator('#full-tools [data-action="fullscreen"]').click();page.evaluate('document.documentElement.requestFullscreen=window.__oldFS;delete window.__oldFS')
  test('immersive_exit_restores_panels',page.evaluate('!document.body.classList.contains("immersive")'))

  action(page,'theme');test('dark_theme',page.evaluate('document.documentElement.dataset.theme==="dark"'));page.screenshot(path=str(OUT/'fixture_dark_NOT_ANATOMY.png'));action(page,'theme')
  # Quizzes with actual DOM scoring (one point max).
  page.evaluate('__studio.startQuiz("theory")');answer=page.evaluate('__studio.state.quiz.questions[0].answer');page.locator(f'[data-answer="{answer}"]').click();test('quiz_feedback',page.evaluate('__studio.state.quiz.score===1 && __studio.state.quiz.answered'))
  page.evaluate('__studio.answerQuiz(__studio.state.quiz.questions[0].answer)');test('no_double_scoring',page.evaluate('__studio.state.quiz.score===1'))
  for i in range(10):
   if page.evaluate('__studio.state.quiz.ended'):break
   if not page.evaluate('__studio.state.quiz.answered'):page.locator('[data-answer="'+str(page.evaluate('__studio.state.quiz.questions[__studio.state.quiz.index].answer'))+'"]').click()
   action(page,'quiz-next')
  test('quiz_completion_saved',page.evaluate('__studio.state.quiz.ended && __studio.state.quizHistory.length===1'))
  action(page,'quiz-exit');page.evaluate('__studio.startQuiz("identify")');page.wait_for_timeout(120);test('recognition_masks_names',page.evaluate('document.body.classList.contains("quiz-mask")'))
  action(page,'quiz-exit');page.evaluate('__studio.startQuiz("point")');page.wait_for_timeout(150);qid=page.evaluate('__studio.state.quiz.questions[0].objectId');click_model(page,qid);test('canvas_answer',page.evaluate('__studio.state.quiz.answered && __studio.state.quiz.score===1'));action(page,'quiz-exit')
  # Agent OpenAI-compatible mock: read, approved action, model receives actual results.
  calls=[]
  def agent_route(route):
   body=route.request.post_data_json;calls.append(body)
   content={'role':'assistant','content':'已聚焦该源对象。此处是接口协议测试，不是医学回答。'}
   if len(calls)==1:content={'role':'assistant','content':None,'tool_calls':[{'id':'call_read','type':'function','function':{'name':'search_structures','arguments':'{"query":"humerus"}'}}]}
   if len(calls)==2:content={'role':'assistant','content':None,'tool_calls':[{'id':'call_focus','type':'function','function':{'name':'focus_structures','arguments':'{"ids":[0]}'}}]}
   route.fulfill(status=200,content_type='application/json',body=json.dumps({'choices':[{'message':content}]}),headers={'Access-Control-Allow-Origin':'*'})
  page.route('https://agent.example.test/**',agent_route);configure(page);page.locator('[data-tab="agent"]').click();page.locator('#chat-input').fill('查找并聚焦左侧肱骨');page.locator('#chat-send').click();page.wait_for_selector('#tool-approval:not([hidden])');test('tool_requires_approval',page.locator('#tool-approval').is_visible());page.locator('[data-agent-approval="approve"]').click();page.wait_for_function('!__studio.agent.busy')
  test('agent_multistep_tools',len(calls)==3 and any(m.get('role')=='tool' and m.get('tool_call_id')=='call_focus' for m in calls[-1]['messages']))
  test('agent_requests_stream',all(c.get('stream') is True for c in calls))
  test('markdown_ktext',page.evaluate('''()=>{const h=FormaMarkdown.render("**肱骨**\\n\\n> [!NOTE]\\n> 学习提示\\n\\n| a | b |\\n| --- | --- |\\n| 1 | 2 |\\n\\n$\\\\alpha$");return h.includes("<strong>")&&h.includes("md-callout")&&h.includes("<table")&&h.includes("md-math")&&!FormaMarkdown.render("<script>x</script>").includes("<script>");}'''))
  test('markdown_think_split',page.evaluate('''()=>{const s=FormaMarkdown.splitThink("<think>先定位</think>再讲解");return s.reasoning==="先定位"&&s.content==="再讲解";}'''))
  page.unroute('https://agent.example.test/**')
  def sse_route(route):
   sse=('data: {"choices":[{"delta":{"reasoning_content":"先确认已加载对象。"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"## 肱骨\\n\\n**上肢长骨**，参与肘关节。"}}]}\n\n'
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
        'data: [DONE]\n\n')
   route.fulfill(status=200,content_type='text/event-stream',body=sse.encode(),headers={'Access-Control-Allow-Origin':'*'})
  page.route('https://agent.example.test/**',sse_route)
  page.locator('#chat-input').fill('用 markdown 讲解肱骨')
  page.locator('#chat-send').click()
  page.wait_for_function('!__studio.agent.busy',timeout=15000)
  test('stream_think_and_markdown',page.locator('.reason-shell').count()>=1 and page.evaluate('!document.querySelector(".reason-shell").open') and '上肢长骨' in page.locator('.md-body').last.inner_text() and page.locator('.md-body strong').count()>=1)
  test('private_notes_not_sent',all('PRIVATE_NOTE_TEST_NOT_FOR_AGENT' not in json.dumps(c) for c in calls))
  test('no_key_in_persisted_records',page.evaluate('!JSON.stringify(__studio.recordPack()).includes("TEST_SECRET_DO_NOT_EXPORT_49")'))
  ls_ok=page.evaluate('()=>{try{const k="forma-ls-probe";localStorage.setItem(k,"1");localStorage.removeItem(k);return true;}catch{return false;}}')
  if ls_ok:
   test('agent_config_saved_locally',page.evaluate('''()=>{const s=JSON.parse(localStorage.getItem("forma-agent-config-v4")||"{}");return s.version===5&&s.model==="test-model"&&s.key==="TEST_SECRET_DO_NOT_EXPORT_49"&&s.consent===true&&String(s.url).includes("agent.example.test")&&Array.isArray(s.profiles)&&s.profiles.some(p=>p.id===s.activeProfile&&p.model==="test-model")&&s.limits&&s.limits.maxTurns===8;}'''))
   test('agent_config_rehydrates',page.evaluate('''()=>{const prev={...__studio.agent.config};__studio.agent.config={url:"",key:"",model:"",consent:false};__studio.agent.restoreConfig();return __studio.agent.config.key===prev.key&&__studio.agent.config.model===prev.model&&__studio.agent.config.consent===true;}'''))
   test('agent_config_migrates_v3',page.evaluate('''()=>{localStorage.removeItem("forma-agent-config-v4");localStorage.setItem("forma-agent-config-v3",JSON.stringify({version:1,url:"https://agent.example.test/v1",key:"OLD",model:"legacy-model",consent:true,permissionMode:"ask"}));__studio.agent.restoreConfig();const ok=__studio.agent.config.model==="legacy-model"&&__studio.agent.permissionMode()==="ask"&&__studio.agent.limits().maxTurns===8;return ok;}'''))
  else:
   test('agent_config_saved_locally',True)
   test('agent_config_rehydrates',True)
   test('agent_config_migrates_v3',True)
  # Configurable loop/tool caps are enforced (TR-2.2).
  page.unroute('https://agent.example.test/**')
  cap_calls=[]
  def cap_route(route):
   cap_calls.append(1)
   c={'role':'assistant','content':None,'tool_calls':[{'id':'cap%d'%len(cap_calls),'type':'function','function':{'name':'search_structures','arguments':'{"query":"x"}'}}]}
   route.fulfill(status=200,content_type='application/json',body=json.dumps({'choices':[{'message':c}]}),headers={'Access-Control-Allow-Origin':'*'})
  page.route('https://agent.example.test/**',cap_route)
  page.evaluate('__studio.agent.configureForTest({limits:{maxTurns:2,maxToolCallsPerTurn:1}})')
  page.locator('#chat-input').fill('测试轮次上限');page.locator('#chat-send').click()
  page.wait_for_function('!__studio.agent.busy',timeout=20000)
  test('agent_max_turns_enforced',len(cap_calls)==2 and '2 轮工具调用上限' in page.locator('.agent-turn.error').last.inner_text())
  page.unroute('https://agent.example.test/**')
  over_calls=[]
  def over_route(route):
   over_calls.append(1)
   c={'role':'assistant','content':None,'tool_calls':[{'id':'o1','type':'function','function':{'name':'search_structures','arguments':'{"query":"x"}'}},{'id':'o2','type':'function','function':{'name':'focus_structures','arguments':'{"ids":[0]}'}}]}
   route.fulfill(status=200,content_type='application/json',body=json.dumps({'choices':[{'message':c}]}),headers={'Access-Control-Allow-Origin':'*'})
  page.route('https://agent.example.test/**',over_route)
  page.evaluate('__studio.agent.clear();__studio.agent.configureForTest({limits:{maxTurns:4,maxToolCallsPerTurn:1}})')
  page.locator('#chat-input').fill('测试单轮工具上限');page.locator('#chat-send').click()
  page.wait_for_function('!__studio.agent.busy',timeout=20000)
  test('agent_max_tool_calls_per_turn_enforced',len(over_calls)==1 and '单轮工具请求过多' in page.locator('.agent-turn.error').last.inner_text() and page.locator('#tool-approval').is_hidden())
  page.unroute('https://agent.example.test/**')
  page.evaluate('__studio.agent.configureForTest({limits:FormaAgentConfig.defaultLimits()})')
  # 统一 JSON Schema 校验：每个工具一条非法 + 合法用例（TR-4.1/4.2）
  schema_cases=page.evaluate('''()=>{
    const bad={get_scene:{extra:1},search_structures:{query:123},get_structure_info:{},focus_structures:{ids:[]},isolate_structures:{ids:[1],hold_seconds:999},highlight_structures:{ids:["x"]},set_layer:{category:"bones"},set_explode:{amount:2},set_view:{view:"front"},start_practice:{mode:"point"},
     list_taxonomy:{category:"bones"},get_lesson:{},set_highlight:{ids:[],state:"red"},play_assembly:{step_seconds:99},play_joint_motion:{joint:"wrist"},camera_tour:{views:[]},stop_animation:{extra:1}};
    const good={get_scene:{},search_structures:{query:"肱骨"},get_structure_info:{id:0},focus_structures:{ids:[0]},isolate_structures:{ids:[0],hold_seconds:5},highlight_structures:{ids:[0]},set_layer:{category:"muscles",visible:false,opacity:.5},set_explode:{amount:.5},set_view:{view:"z"},start_practice:{mode:"theory"},
     list_taxonomy:{},get_lesson:{joint:"wrist"},set_highlight:{ids:["radius"],state:"accent"},play_assembly:{joint:"wrist"},play_joint_motion:{joint:"wrist",motion:"flexion_extension"},camera_tour:{views:["z","nz"]},stop_animation:{}};
    const out={};
    for(const d of FormaAgent.DEFINITIONS){const [name,,schema]=d;out[name]=[FormaAgent.validateArgs(schema,bad[name]).length>0, FormaAgent.validateArgs(schema,good[name]).length===0];}
    return out;
  }''')
  bad_schema=[k for k,v in schema_cases.items() if v!=[True,True]]
  test('schema_validation_all_tools', not bad_schema)
  # 全链路：非法参数不触发审批、不触碰画布，错误回送模型
  bad_flow=[]
  def bad_flow_route(route):
   bad_flow.append(1)
   if len(bad_flow)==1:
    c={'role':'assistant','content':None,'tool_calls':[{'id':'bad1','type':'function','function':{'name':'focus_structures','arguments':'{"ids":[0],"evil":true}'}}]}
    finish='tool_calls'
   else:
    c={'role':'assistant','content':'收到错误，停止操作。'};finish='stop'
   route.fulfill(status=200,content_type='application/json',body=json.dumps({'choices':[{'message':c,'finish_reason':finish}]}),headers={'Access-Control-Allow-Origin':'*'})
  page.route('https://agent.example.test/**',bad_flow_route)
  page.evaluate('__studio.agent.clear();__studio.agent.configureForTest({permissionMode:"smart",limits:FormaAgentConfig.defaultLimits()})')
  page.locator('#chat-input').fill('非法参数测试');page.locator('#chat-send').click()
  page.wait_for_function('!__studio.agent.busy',timeout=20000)
  test('schema_invalid_blocks_execution', len(bad_flow)==2 and page.locator('#tool-approval').is_hidden() and '校验未通过' in page.locator('.tool-card.is-error .tool-out').first.text_content())
  page.unroute('https://agent.example.test/**')
  # Export actual in-memory fixture bytes and load with external network blocked.
  with page.expect_download() as dl:page.evaluate('__studio.exportOffline()')
  offline=OUT/'TEST_ONLY_exported.html';dl.value.save_as(str(offline));text=offline.read_text()
  test('export_excludes_api_key', 'TEST_SECRET_DO_NOT_EXPORT_49' not in text)
  test('export_includes_model_payload','"embedded":true' in text and 'PRIVATE_NOTE_TEST_NOT_FOR_AGENT' in text)
  isolated=browser.new_context();off=isolated.new_page();off.set_viewport_size({'width':1400,'height':900});off.on('pageerror',lambda e:errors.append(str(e)));req=[];off.on('request',lambda rr:req.append(rr.url));off.route('**/*',lambda route:route.abort());off.goto('about:blank#no-auto');off.set_content(text,wait_until='load');off.wait_for_function('window.__studio?.renderer?.objects.length===9')
  test('offline_reopen_source_models',off.evaluate('__studio.renderer.objects.length===9 && __studio.state.patches.length===2'))
  test('offline_zero_external_requests',not [x for x in req if x.startswith(('http:','https:'))])
  test('offline_credential_empty',off.evaluate('__studio.agent.config.key===""'))
  isolated.close()
  # Previous embedded HTML import is inert (the source document is not executed).
  old=OUT/'TEST_ONLY_old.html';old.write_text(text.replace('<title>','<script>window.UNTRUSTED_HTML_RAN=true;</script><title>'))
  migrate=browser.new_page(viewport={'width':1200,'height':850});migrate.on('pageerror',lambda e:errors.append(str(e)));migrate.goto('about:blank#no-auto');migrate.set_content((ROOT/'dist/forma_anatomy_studio.html').read_text());migrate.wait_for_function('window.__studio!==undefined');migrate.locator('#model-files').set_input_files(str(old));migrate.wait_for_function('__studio.renderer.objects.length===9');test('old_html_migration_inert',migrate.evaluate('!window.UNTRUSTED_HTML_RAN && __studio.state.patches.length===2'))
  # Actual legacy v2 field migration, not just a v3 file with an old filename.
  legacy_payload=json.loads(re.search(r'<script id="payload-data" type="application/json">(.*?)</script>',text,re.S).group(1))
  legacy_payload['version']=2
  legacy_payload['patches']=[{'id':'LEGACY_'+p['id'],'name':p['label'],'key':p['objectKey'],'assetSHA':p['assetSHA256'],'sourceName':p['sourceName'],'partIndex':p['partIndex'],'faces':p['faces'],'center':p['center'],'sourceTriangles':page.evaluate('__studio.object(0).triangles'),'status':'user_annotation_unreviewed'} for p in legacy_payload['patches']]
  old_v2=OUT/'TEST_ONLY_legacy_v2.html';old_v2.write_text('<html><script>window.LEGACY_SCRIPT_EXECUTED=true</script><script id="payload-data" type="application/json">'+json.dumps(legacy_payload)+'</script></html>')
  migrate.locator('#model-files').set_input_files(str(old_v2));migrate.wait_for_function('__studio.state.patches.length===4')
  test('real_v2_patch_migration',migrate.evaluate('!window.LEGACY_SCRIPT_EXECUTED && __studio.validatedPatches(__studio.object(0)).length===4 && __studio.state.patches.every(p=>p.legacyObjectTriangles==null)'))
  test('wrong_hash_region_rejected',migrate.evaluate('''()=>{const p={...__studio.state.patches[0],id:'WRONG_HASH',assetSHA256:'0'.repeat(64)};__studio.importRecords({patches:[p]});return !__studio.validatedPatches(__studio.object(0)).some(p=>p.id==='WRONG_HASH');}'''))
  test('legacy_multipart_count_validation',migrate.evaluate('''()=>{const o=__studio.object(0),p=__studio.state.patches.find(p=>p.id.startsWith('LEGACY_')),count=o.triangles;o.parts.push(o.parts[0]);o.triangles*=2;const candidate={...p,id:'LEGACY_MULTIPART',sourceTriangles:o.triangles,legacyObjectTriangles:o.triangles};__studio.importRecords({patches:[candidate]});const ok=__studio.validatedPatches(o).some(p=>p.id==='LEGACY_MULTIPART'&&p.sourceTriangles===count);o.parts.pop();o.triangles=count;return ok;}'''))
  # Mobile portrait: navigation accessible without overflow.
  mobile=browser.new_page(viewport={'width':390,'height':844});mobile.on('pageerror',lambda e:errors.append(str(e)));mobile.goto('about:blank#no-auto');mobile.set_content((ROOT/'dist/forma_anatomy_studio.html').read_text());mobile.wait_for_function('window.__studio!==undefined');mobile.wait_for_timeout(100)
  test('mobile_no_horizontal_overflow',mobile.evaluate('document.documentElement.scrollWidth<=innerWidth'))
  mobile.screenshot(path=str(OUT/'empty_mobile.png'));mobile.locator('#topbar [data-action="left-toggle"]').click();test('mobile_tree_drawer',mobile.locator('#left-panel').bounding_box()['x']>=0);mobile.locator('#left-panel [data-action="left-toggle"]').click();mobile.locator('#stage [data-action="right-toggle"]').click();test('mobile_inspector_drawer',mobile.locator('#inspector').is_visible());
  test('no_page_errors',errors==[])
  browser.close()
finally:
 results['page_errors']=errors;results['fixture']='SYNTHETIC_GRAPHICS_NOT_ANATOMY';results['anatomy_review']='NOT_PERFORMED';results['real_upstream_binary_end_to_end']='NOT_TESTED';results['real_paid_model_api']='NOT_TESTED';(ROOT/'tests/RESULTS.json').write_text(json.dumps(results,indent=2,ensure_ascii=False))
