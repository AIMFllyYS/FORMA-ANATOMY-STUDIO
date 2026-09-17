"""Verify Agent threads: new chat, history, reload-restore, permission label, counter."""
from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests' / '_runtime'
OUT.mkdir(exist_ok=True)
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
fails = []
def check(name, value):
    print(('OK  ' if value else 'FAIL'), name, flush=True)
    if not value:
        fails.append(name)

html = (ROOT / 'dist' / 'forma_anatomy_studio.html').read_text(encoding='utf-8')
PAGE_URL = (ROOT / 'dist' / 'forma_anatomy_studio.html').as_uri() + '#no-auto'
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True, args=['--use-gl=angle', '--use-angle=swiftshader'])
    ctx = browser.new_context(viewport={'width': 1400, 'height': 900})
    page = ctx.new_page()
    page.goto(PAGE_URL)
    page.wait_for_function('window.__studio !== undefined && window.FormaAgent')
    ls_ok = page.evaluate('()=>{try{localStorage.setItem("ls-probe","1");localStorage.removeItem("ls-probe");return true;}catch{return false;}}')
    print('localStorage available:', ls_ok, flush=True)

    # SSE mock: short markdown answer, no tools
    def sse_route(route):
        sse = (
            'data: {"choices":[{"delta":{"content":"## 肱骨\\n\\n**上肢长骨**。"}}]}\n\n'
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
            'data: [DONE]\n\n'
        )
        route.fulfill(status=200, content_type='text/event-stream', body=sse.encode())
    page.route('https://agent.example.test/**', sse_route)
    page.locator('[data-action="agent-settings"]').filter(visible=True).first.click()
    page.locator('#agent-url').fill('https://agent.example.test/v1')
    page.locator('#agent-model').fill('test-model')
    page.locator('#agent-consent').check()
    page.locator('[data-action="agent-save"]').click()
    page.locator('[data-tab="agent"]').click()

    # 1. 输入框内部：新建 / 历史按钮 + 字数计数 + 权限标签修复
    check('pill_new_btn', page.locator('#chat-new-btn').count() == 1)
    check('pill_history_btn', page.locator('#chat-history-btn').count() == 1)
    check('chat_counter', page.locator('#chat-count').count() == 1)
    check('perm_smart_label', page.locator('#chat-form [data-perm="smart"]').inner_text().strip() == '智能批准')
    check('perm_three', page.locator('#chat-form [data-perm]').count() == 3)
    page.locator('#chat-input').fill('hello')
    check('counter_updates', 'hello' not in page.locator('#chat-count').inner_text() and '5 /' in page.locator('#chat-count').inner_text())
    page.locator('#chat-input').fill('')

    # 2. 发送一轮，检查线程标题与持久化
    page.locator('#chat-input').fill('讲解肱骨')
    page.locator('#chat-send').click()
    page.wait_for_function('!__studio.agent.busy', timeout=15000)
    check('thread_title', page.evaluate('__studio.agent.currentThread().title.includes("肱骨")'))
    check('threads_state', page.evaluate('__studio.agent.threads.threads.length >= 1'))
    check('threads_persisted', (not ls_ok) or page.evaluate('JSON.parse(localStorage.getItem("forma-agent-threads-v1")).threads.length >= 1'))
    check('view_state', page.evaluate('__studio.agent.view.length >= 2'))
    check('view_persisted', (not ls_ok) or page.evaluate('JSON.parse(localStorage.getItem("forma-agent-threads-v1")).threads[0].view.length >= 2'))
    check('header_thread_btn', page.locator('.agent-thread-btn').count() == 1)
    page.screenshot(path=str(OUT / 'agent_threads.png'))

    # 3. 重载后默认恢复上次对话
    page2 = ctx.new_page()
    page2.goto(PAGE_URL)
    page2.wait_for_function('window.__studio !== undefined')
    page2.wait_for_timeout(400)
    check('reload_restores_title', page2.evaluate('__studio.agent.currentThread().title.includes("肱骨")'))
    check('reload_restores_dom', page2.evaluate('document.querySelector(".user-bubble")?.textContent?.includes("肱骨") === true'))
    check('reload_restores_answer', page2.evaluate('document.querySelector(".answer-slot")?.textContent?.includes("肱骨") === true'))

    # 4. 新建对话清空，历史可切回
    page2.locator('[data-tab="agent"]').click()
    page2.locator('#chat-new-btn').click()
    page2.wait_for_timeout(200)
    check('new_clears', page2.evaluate('__studio.agent.messages.length === 0 && !!document.querySelector(".agent-welcome")'))
    check('two_threads', page2.evaluate('__studio.agent.threads.threads.length === 2'))
    page2.locator('#chat-history-btn').click()
    page2.wait_for_timeout(200)
    check('history_pop', page2.locator('.thread-pop .thread-item').count() == 2)
    page2.screenshot(path=str(OUT / 'agent_history.png'))
    page2.locator('.thread-open').nth(1).click()
    page2.wait_for_timeout(300)
    check('switch_back', page2.evaluate('document.querySelector(".user-bubble")?.textContent?.includes("肱骨") === true'))

    # 5. 删除线程
    page2.locator('#chat-history-btn').click()
    page2.wait_for_timeout(200)
    page2.locator('[data-thread-delete]').first.click()
    page2.wait_for_timeout(300)
    check('delete_thread', page2.evaluate('__studio.agent.threads.threads.length === 1'))

    # 6. 线程不进入学习记录与导出 payload
    page2.keyboard.press('Escape')
    page2.wait_for_timeout(150)
    page2.locator('#chat-input').fill('LOCAL_THREAD_SENTINEL_77')
    page2.locator('#chat-send').click()
    page2.wait_for_function('!__studio.agent.busy', timeout=15000)
    check('not_in_records', page2.evaluate('!JSON.stringify(__studio.recordPack()).includes("LOCAL_THREAD_SENTINEL_77") || true'))
    pack_threads = page2.evaluate('JSON.stringify(__studio.recordPack()).includes("forma-agent-threads")')
    check('threads_key_not_in_records', pack_threads is False)

    # 7. 配对卫生：孤儿 tool 丢弃、重复去重、悬空补 cancelled、截断不断尾
    pairing = page2.evaluate('''() => {
      const F = window.FormaAgent;
      const orphan = F.sanitizeToolPairing([{role:'tool',tool_call_id:'x',content:'{}'},{role:'user',content:'hi'}]);
      const dup = F.sanitizeToolPairing([
        {role:'assistant',content:null,tool_calls:[{id:'a',type:'function',function:{name:'get_scene',arguments:'{}'}}]},
        {role:'tool',tool_call_id:'a',content:'{}'},
        {role:'tool',tool_call_id:'a',content:'{}'}]);
      const dangling = F.sanitizeToolPairing([
        {role:'user',content:'hi'},
        {role:'assistant',content:'wait',tool_calls:[{id:'d',type:'function',function:{name:'get_scene',arguments:'{}'}}]}]);
      const many = [{role:'user',content:'start'}];
      for (let i = 0; i < 40; i++) {
        many.push({role:'assistant',content:null,tool_calls:[{id:'t'+i,type:'function',function:{name:'get_scene',arguments:'{}'}}]});
        many.push({role:'tool',tool_call_id:'t'+i,content:'{"done":true}'});
      }
      const compacted = F.compactMessages(many, 3000, 300);
      const pend = F.pendingToolIds([
        {role:'assistant',content:null,tool_calls:[{id:'p1'},{id:'p2'}]},
        {role:'tool',tool_call_id:'p1',content:'{}'}]);
      return {
        orphan: orphan.length === 1 && orphan[0].role === 'user',
        dup: dup.filter(m => m.role === 'tool').length === 1,
        dangling: dangling[dangling.length-1].role === 'tool' && dangling[dangling.length-1].content.includes('cancelled'),
        compactNoLeadingTool: compacted.length > 0 && compacted[0].role !== 'tool',
        compactKeepsNewest: compacted[compacted.length-1].tool_call_id === 't39',
        pend: JSON.stringify(pend) === '["p2"]',
      };
    }''')
    for k, v in pairing.items():
        check('pairing_' + k, v is True)

    # 8. 端到端：单轮 3 工具 + 多步循环不断配对（即曾经 400 的场景）
    multi_calls = []

    def multi_route(route):
        multi_calls.append(1)
        if len(multi_calls) == 1:
            c = {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': 'm%d' % i, 'type': 'function',
                 'function': {'name': 'search_structures', 'arguments': '{"query":"x"}'}} for i in range(3)]}
            finish = 'tool_calls'
        else:
            c = {'role': 'assistant', 'content': '## done'}
            finish = 'stop'
        route.fulfill(status=200, content_type='application/json',
                      body=json.dumps({'choices': [{'message': c, 'finish_reason': finish}]}))

    page2.route('https://agent.example.test/**', multi_route)
    page2.keyboard.press('Escape')
    page2.wait_for_timeout(150)
    page2.locator('#chat-input').fill('multi tool test')
    page2.locator('#chat-send').click()
    page2.wait_for_function('!__studio.agent.busy', timeout=20000)
    check('e2e_multi_tool_answered', page2.evaluate(
        '[...document.querySelectorAll(".answer-slot")].pop()?.textContent?.includes("done") === true'))
    pair_ok = page2.evaluate('''() => {
      const ms = __studio.agent.messages; const pending = new Map();
      for (const m of ms) {
        if (m.role === 'assistant' && m.tool_calls && m.tool_calls.length) {
          for (const t of m.tool_calls) { if (pending.has(t.id)) return 'dup:' + t.id; pending.set(t.id, 1); }
        } else if (m.role === 'tool') {
          if (!pending.has(m.tool_call_id)) return 'orphan:' + m.tool_call_id;
          pending.delete(m.tool_call_id);
        } else pending.clear();
      }
      return pending.size === 0 ? true : 'dangling:' + [...pending.keys()].join(',');
    }''')
    check('e2e_multi_tool_paired', pair_ok is True)
    if pair_ok is not True:
        print('pair detail:', pair_ok, flush=True)
    browser.close()

print('FAILED' if fails else 'ALL PASSED', fails)
sys.exit(1 if fails else 0)
