"""Pause-anytime + FIFO message queue integration tests.

A real loopback HTTP server holds selected requests open (in its own thread)
until the test releases them, giving a deterministic "agent busy" window.
Synthetic protocol only, never anatomy.
"""
from pathlib import Path
import json, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
results={};errors=[]
def check(name,cond):
 results[name]=bool(cond);print(name,results[name],flush=True)
 if not cond:raise AssertionError(name)
def action(page,name):
 page.locator('[data-action="'+name+'"]').first.click()

STATE={'n':0,'lock':threading.Lock(),'gates':{},'users':[]}
def sse(answer):
 return ('data: {"choices":[{"delta":{"content":"%s"}}]}\n\n'
         'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
         'data: [DONE]\n\n'%answer).encode()
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def _cors(self):
  self.send_header('Access-Control-Allow-Origin','*')
  self.send_header('Access-Control-Allow-Headers','authorization,content-type')
  self.send_header('Access-Control-Allow-Methods','POST,OPTIONS')
 def do_OPTIONS(self):
  self.send_response(204);self._cors();self.end_headers()
 def do_POST(self):
  ln=int(self.headers.get('Content-Length') or 0)
  body=json.loads(self.rfile.read(ln) or b'{}')
  users=[m.get('content') for m in body.get('messages',[]) if m.get('role')=='user']
  with STATE['lock']:
   STATE['n']+=1;i=STATE['n']
  if users:STATE['users'].append(users[-1])
  if i in (1,3):
   ev=threading.Event();STATE['gates'][i]=ev;ev.wait(30)
  ans={1:'ANSWER_1',2:'ANSWER_2',3:'ANSWER_3_SHOULD_NOT_APPEAR'}.get(i,'ANSWER_DONE')
  self.send_response(200);self._cors();self.send_header('Content-Type','text/event-stream');self.send_header('Cache-Control','no-store');self.end_headers()
  try:self.wfile.write(sse(ans));self.wfile.flush()
  except Exception:pass
srv=ThreadingHTTPServer(('127.0.0.1',0),Handler);port=srv.server_address[1]
threading.Thread(target=srv.serve_forever,daemon=True).start()
BASE='http://127.0.0.1:%d/v1'%port
def configure(page):
 action(page,'agent-settings')
 page.locator('#agent-url').fill(BASE)
 page.locator('#agent-model').fill('test-model')
 page.locator('#agent-consent').check()
 action(page,'agent-save')
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  page=browser.new_page(viewport={'width':1400,'height':900})
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('about:blank#no-auto')
  page.set_content((ROOT/'dist/forma_anatomy_studio.html').read_text(),wait_until='load')
  page.wait_for_function('window.__studio !== undefined && window.__studio.agent')
  configure(page)
  page.locator('[data-tab="agent"]').click()

  # --- Turn 1 held open at the server: queue two more messages while busy ---
  page.locator('#chat-input').fill('Q1');page.locator('#chat-send').click()
  page.wait_for_function('__studio.agent.busy === true')
  # Confirm the first POST has reached (and is held by) the server before enqueuing.
  for _ in range(300):
   if STATE['n']>=1:break
   page.wait_for_timeout(50)
  check('first_request_held',STATE['n']==1)
  page.wait_for_timeout(120)
  check('stop_visible_while_busy',page.locator('#chat-stop').is_visible())
  check('send_enabled_while_busy',page.locator('#chat-send').is_enabled())

  page.locator('#chat-input').fill('Q2');page.locator('#chat-send').click()
  page.locator('#chat-input').fill('Q3');page.locator('#chat-send').click()
  page.wait_for_selector('.agent-turn.user.queued >> nth=1')
  check('two_queued_bubbles',page.locator('.agent-turn.user.queued').count()==2)
  check('queue_badge_shows_2',page.locator('#chat-stop').get_attribute('data-queue')=='2')
  check('only_one_inflight_request',STATE['n']==1)
  check('queued_text_shown','Q2' in page.locator('.agent-turn.user.queued').first.inner_text())

  # Undo the last queued message (Q3).
  page.locator('.agent-turn.user.queued').last.locator('.queued-cancel').click()
  page.wait_for_timeout(100)
  check('undo_removes_bubble',page.locator('.agent-turn.user.queued').count()==1)
  check('queue_badge_shows_1',page.locator('#chat-stop').get_attribute('data-queue')=='1')

  # Release turn 1 -> Q2 auto-sends next, queue drains automatically.
  STATE['gates'][1].set()
  page.wait_for_function('__studio.agent.busy === false',timeout=15000)
  check('queued_auto_sent_in_order',STATE['users'][-2:]==['Q1','Q2'])
  check('cancelled_never_sent','Q3' not in STATE['users'])
  check('queue_cleared_after_drain',page.locator('.agent-turn.user.queued').count()==0)
  chat=page.locator('#chat-messages').inner_text()
  check('both_answers_rendered','ANSWER_1' in chat and 'ANSWER_2' in chat)
  check('stop_hidden_when_idle',page.locator('#chat-stop').is_hidden())

  # --- Pause anytime: request 3 held open, enqueue one, then stop ---
  page.locator('#chat-input').fill('STOP_ME');page.locator('#chat-send').click()
  page.wait_for_function('__studio.agent.busy === true')
  # 与首轮一致：等这一轮请求真正抵达并被服务器挂起后再入队，避免“停止时请求还没发出”的竞态。
  for _ in range(300):
   if STATE['n']>=3:break
   page.wait_for_timeout(50)
  check('held_request_before_stop',STATE['n']==3)
  page.locator('#chat-input').fill('AFTER_STOP');page.locator('#chat-send').click()
  page.wait_for_selector('.agent-turn.user.queued')
  action(page,'chat-stop')
  page.wait_for_function('__studio.agent.busy === false',timeout=8000)
  err=page.locator('.agent-turn.error').last.inner_text()
  check('stopped_message_shown','已停止' in err)
  check('queue_discarded_on_stop',page.locator('.agent-turn.user.queued').count()==0 and 'AFTER_STOP' not in STATE['users'])
  check('held_answer_not_rendered','ANSWER_3_SHOULD_NOT_APPEAR' not in page.locator('#chat-messages').inner_text())
  # 请求 3 可能在中止时尚未抵达服务器（停止即取消），门闩只在已建立时释放。
  if 3 in STATE['gates']:STATE['gates'][3].set()
  page.wait_for_timeout(200)
  # Can immediately start a new turn after stopping.
  page.locator('#chat-input').fill('RESUME');page.locator('#chat-send').click()
  page.wait_for_function('__studio.agent.busy === true')
  page.wait_for_function('__studio.agent.busy === false',timeout=10000)
  check('resume_after_stop_works','ANSWER_DONE' in page.locator('#chat-messages').inner_text())
  check('no_page_errors',errors==[])
  browser.close()
finally:
  for ev in STATE['gates'].values():ev.set()
  srv.shutdown()
  results['page_errors']=errors
  (ROOT/'tests/AGENT_QUEUE_RESULTS.json').write_text(json.dumps(results,indent=2,ensure_ascii=False))
  print(json.dumps(results,ensure_ascii=False,indent=2))
  if errors:sys.exit(1)
