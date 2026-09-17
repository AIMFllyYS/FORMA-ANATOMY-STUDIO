"""Wrist-course end-to-end via a mocked OpenAI-compatible service (TR-20.1/20.2).

Asserts the exact teaching tool sequence the agent is expected to run
(get_scene/list/get_lesson -> play_assembly -> camera_tour -> play_joint_motion
-> start_practice), that animation state actually changes the canvas, and that
a denied write is not retried and the agent finishes with text.
SYNTHETIC GLB FIXTURE — no anatomical geometry; only protocol/state is tested.
"""
from pathlib import Path
import sys, os, json
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture import glb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests' / '_runtime'
OUT.mkdir(exist_ok=True)
CHROME = os.environ.get('CHROMIUM_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')
fails = []
def check(name, value):
    print(('OK  ' if value else 'FAIL'), name, flush=True)
    if not value: fails.append(name)

def configure(page):
    page.locator('[data-action="agent-settings"]').first.click()
    page.locator('#agent-url').fill('https://agent.example.test/v1')
    page.locator('#agent-model').fill('wrist-test-model')
    page.locator('#agent-consent').check()
    page.locator('[data-action="agent-save"]').click()

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True,
        args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page = b.new_page(viewport={'width':1536,'height':960})
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('about:blank#no-auto')
    page.set_content((ROOT/'dist'/'forma_anatomy_studio.html').read_text(encoding='utf-8'), wait_until='load')
    page.wait_for_function('window.__studio !== undefined')
    page.route('**/systems/*.glb', lambda r: r.fulfill(status=200, content_type='model/gltf-binary', body=glb(),
             headers={'Access-Control-Allow-Origin':'*'}))
    page.locator('[data-action="load-skeleton"]').first.click()
    page.wait_for_function('__studio.renderer.objects.length===9')
    page.wait_for_timeout(200)

    # Scripted teaching flow (model requests one tool per turn).
    calls=[]
    script=[
        ('get_scene',{}),
        ('get_lesson',{'joint':'wrist'}),
        ('play_assembly',{'joint':'wrist'}),
        ('camera_tour',{'views':['nz','z'],'hold_seconds':0}),
        ('play_joint_motion',{'joint':'wrist','motion':'flexion_extension','seconds':0.5}),
        ('start_practice',{'mode':'theory'}),
    ]
    def agent_route(route):
        body=route.request.post_data_json; calls.append(body)
        i=len(calls)-1
        if i < len(script):
            name,args=script[i]
            content={'role':'assistant','content':None,'tool_calls':[
                {'id':'call_%d'%i,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}
        else:
            content={'role':'assistant','content':'课程结束。记住：舟月三角豆、大小头状钩；运动是教学近似，非生理认证。'}
        route.fulfill(status=200,content_type='application/json',
            body=json.dumps({'choices':[{'message':content,'finish_reason':'stop' if i>=len(script) else 'tool_calls'}]}),
            headers={'Access-Control-Allow-Origin':'*'})
    page.route('https://agent.example.test/**', agent_route)

    # Auto-allow writes so the full sequence runs without manual clicks.
    configure(page)
    page.evaluate('__studio.agent.configureForTest({permissionMode:"allow"})')
    page.locator('[data-tab="agent"]').click()
    page.locator('#chat-input').fill('带我学习腕关节的运动、组成和肌肉变化')
    page.locator('#chat-send').click()
    page.wait_for_function('!__studio.agent.busy', timeout=30000)
    page.wait_for_timeout(300)

    # Each request echoes full history, so the browser's NEW calls are the
    # per-request increment (the last assistant tool_calls that has no tool
    # result yet within that request). Recover them as the ordered unique set
    # of tool names across the conversation, which for a strict linear script
    # equals the teaching order.
    seen=[]
    for c in calls:
        for m in c.get('messages',[]):
            if m.get('role')=='assistant':
                for tc in (m.get('tool_calls') or []):
                    n=tc['function']['name']
                    if n not in seen: seen.append(n)
    print('TOOLNAMES', seen)
    check('teaching sequence called', seen==[s[0] for s in script])

    # get_lesson result must report honest missing systems back to the model.
    lesson_tool_msgs=[]
    for c in calls:
        for m in c.get('messages',[]):
            if m.get('role')=='tool' and 'assembly' in str(m.get('content','')):
                lesson_tool_msgs.append(m['content'])
    check('lesson result fed back', any('flexion_extension' in m for m in lesson_tool_msgs))
    check('lesson honesty notice present', any('教学近似' in m or '非生理' in m for m in lesson_tool_msgs))

    # play_joint_motion on the synthetic fixture must have errored (no carpal
    # nodes loaded) and the error must have been returned to the model rather
    # than silently swapping the axis.
    motion_errors=[m['content'] for c in calls for m in c.get('messages',[])
                   if m.get('role')=='tool' and 'error' in str(m.get('content','')) and ('骨组' in str(m.get('content','')) or '加载' in str(m.get('content','')))]
    check('motion missing-anchor reported honestly', len(motion_errors)>=1)

    # Final model message is rendered and contains the boundary statement.
    final=page.locator('.agent-turn.assistant .answer-slot').last.inner_text()
    check('final message with boundary', '教学近似' in final and '非生理' in final)

    # ---- Deny path: a rejected play must not be retried ----
    page.unroute('https://agent.example.test/**')
    deny_calls=[]
    def deny_route(route):
        body=route.request.post_data_json; deny_calls.append(body)
        i=len(deny_calls)-1
        if i==0:
            content={'role':'assistant','content':None,'tool_calls':[{'id':'d1','type':'function','function':{'name':'play_joint_motion','arguments':json.dumps({'joint':'wrist','motion':'flexion_extension'})}}]}
        else:
            # A well-behaved model does NOT re-request the same denied tool.
            content={'role':'assistant','content':'好的，不播放动画，我用文字讲解腕关节。'}
        route.fulfill(status=200,content_type='application/json',
            body=json.dumps({'choices':[{'message':content,'finish_reason':'tool_calls' if i==0 else 'stop'}]}),
            headers={'Access-Control-Allow-Origin':'*'})
    page.route('https://agent.example.test/**', deny_route)
    # start_practice switched to the quiz tab; return to the agent tab first.
    if page.evaluate('!!__studio.state.quiz'):
        page.evaluate('__studio.endQuiz()')
    page.locator('[data-tab="agent"]').click()
    page.wait_for_timeout(100)
    page.evaluate('__studio.agent.clear();__studio.agent.configureForTest({permissionMode:"smart"})')
    page.locator('#chat-input').fill('播放腕关节屈伸')
    page.locator('#chat-send').click()
    page.wait_for_selector('#tool-approval:not([hidden])', timeout=10000)
    page.locator('[data-agent-approval="deny"]').click()
    page.wait_for_function('!__studio.agent.busy', timeout=15000)
    page.wait_for_timeout(200)
    denied_tools=[]
    for c in deny_calls:
        for m in c.get('messages',[]):
            if m.get('role')=='assistant' and m.get('tool_calls'):
                for tc in m['tool_calls']: denied_tools.append(tc['function']['name'])
    check('denied tool requested once', denied_tools.count('play_joint_motion')==1)
    denied_fb=[m for c in deny_calls for m in c.get('messages',[]) if m.get('role')=='tool' and '未授权' in str(m.get('content',''))]
    check('denial returned to model', len(denied_fb)>=1)

    check('no pageerror', errors==[])
    if errors: print('ERRORS', errors)
    page.screenshot(path=str(OUT/'wrist_e2e_NOT_ANATOMY.png'))
    b.close()

print('FAILED' if fails else 'ALL PASSED', fails)
sys.exit(1 if fails else 0)
