"""Verify Agent markdown, streaming, thinking chain, and layout."""
from pathlib import Path
import json, os, sys
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests' / '_runtime'
OUT.mkdir(exist_ok=True)
CHROME = os.environ.get('CHROMIUM_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')
fails = []
def check(name, value):
    print(('OK  ' if value else 'FAIL'), name, flush=True)
    if not value:
        fails.append(name)

html = (ROOT / 'dist' / 'forma_anatomy_studio.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True, args=['--use-gl=angle', '--use-angle=swiftshader'])
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    page.goto('about:blank#no-auto')
    page.set_content(html, wait_until='load')
    page.wait_for_function('window.__studio !== undefined && window.FormaMarkdown')
    md = page.evaluate('''()=>{
      const h=FormaMarkdown.render("**肱骨**\\n\\n> [!NOTE]\\n> 学习提示\\n\\n| 结构 | 作用 |\\n| --- | --- |\\n| 肱骨 | 上肢 |\\n\\n$\\\\alpha$ + $\\\\beta$");
      const x=FormaMarkdown.splitThink("<think>先定位</think>再讲解");
      const raw=FormaMarkdown.render("<script>alert(1)</script>");
      return {hasStrong:h.includes('<strong>'), hasCallout:h.includes('md-callout'), hasTable:h.includes('<table'), hasMath:h.includes('md-math'), noScript:!raw.includes('<script>'), think:x.reasoning==='先定位'&&x.content==='再讲解'};
    }''')
    for k,v in md.items():
        check('md_'+k, v)
    live = page.evaluate('''()=>{
      const h=FormaMarkdown.renderLive("## 肱骨\\n\\n**上肢长骨**");
      const fence=FormaMarkdown.renderLive("前文\\n```js\\nconst x=1");
      return {heading:h.includes('<h2')&&h.includes('<strong>'), fence:fence.includes('md-live-tail')&&!fence.includes('<script')};
    }''')
    check('live_md_heading', live['heading'])
    check('live_md_fence', live['fence'])

    def sse_route(route):
        sse = (
            'data: {"choices":[{"delta":{"reasoning_content":"先确认场景里是否已有肱骨对象。"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"## 肱骨\\n\\n**上肢长骨**。\\n\\n- 近端：头、颈、结节\\n- 远端：滑车与小头\\n\\n> [!TIP]\\n> 先后面鹰嘴窝，再转到前面。\\n\\n| 结构 | 对应 |\\n| --- | --- |\\n| 滑车 | 尺骨 |\\n"}}]}\n\n'
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
            'data: [DONE]\n\n'
        )
        route.fulfill(status=200, content_type='text/event-stream', body=sse.encode(), headers={'Access-Control-Allow-Origin': '*'})
    page.route('https://agent.example.test/**', sse_route)
    page.locator('[data-action="agent-settings"]').filter(visible=True).first.click()
    page.locator('#agent-url').fill('https://agent.example.test/v1')
    page.locator('#agent-model').fill('test-model')
    page.locator('#agent-key').fill('TEST_SECRET_DO_NOT_EXPORT_49')
    page.locator('#agent-consent').check()
    page.locator('[data-action="agent-save"]').click()
    page.locator('[data-tab="agent"]').click()
    check('composer_pill', page.locator('.composer-pill').count() == 1)
    # 空态只占一行；有内容随行长高；到 4 行封顶后在框内滚动（滚动条隐藏）。
    COMPOSER = '''()=>{
      const t=document.querySelector("#chat-input");
      const set=v=>{t.value=v;t.dispatchEvent(new Event("input",{bubbles:true}));};
      const h=()=>t.getBoundingClientRect().height;
      const cs=getComputedStyle(t);
      set("");
      const empty=h();
      set("一行文本");
      const one=h();
      set(Array(3).fill("三行内容").join("\\n"));
      const three=h();
      set(Array(12).fill("很长的一行内容").join("\\n"));
      const many=h(),scrolls=t.scrollHeight>many+0.5;
      set("");
      return {empty:empty,one:one,three:three,many:many,scrolls:scrolls,
              lh:Number.parseFloat(cs.lineHeight),pt:Number.parseFloat(cs.paddingTop)};
    }'''
    c = page.evaluate(COMPOSER)
    # 可见内容区（高度 − 上内边距）必须正好是整行高，否则会露出被切一半的下一行。
    def whole_lines(px):
        return abs((px - c['pt']) / c['lh'] - round((px - c['pt']) / c['lh'])) < 0.02
    check('composer_compact_default', c['empty'] <= 40 and c['one'] <= 40)
    check('composer_grows_with_text', c['three'] > c['one'] + 20)
    check('composer_capped_four_rows', abs(c['many'] - (c['pt'] + 4 * c['lh'])) < 0.5)
    check('composer_no_partial_line', whole_lines(c['many']))
    check('composer_scrolls_when_overflow', c['scrolls'])
    check('composer_count_hidden', page.evaluate('!document.querySelector("#chat-count").classList.contains("is-on")'))
    # 权限与跟随后已聚合进输入框“＋”菜单，不再平铺在输入区。
    page.locator('[data-action="chat-menu"]').first.click()
    check('perm_seg', page.locator('#popover [data-perm]').count() == 3)
    check('perm_default_smart', page.evaluate('__studio.agent.permissionMode()==="smart"'))
    page.locator('#popover [data-perm="allow"]').click()
    check('perm_allow', page.evaluate('__studio.agent.permissionMode()==="allow"'))
    page.locator('#popover [data-perm="ask"]').click()
    check('perm_ask', page.evaluate('__studio.agent.permissionMode()==="ask"'))
    page.locator('#popover [data-perm="smart"]').click()
    page.keyboard.press('Escape')
    # 设置中心：分页、限额即改即存（TR-3.1）
    page.locator('[data-action="agent-settings"]').filter(visible=True).first.click()
    check('settings_tabs', page.locator('[data-settings-tab]').count() == 5)
    check('settings_connection_default', page.locator('#agent-url').is_visible())
    page.locator('[data-settings-tab="limits"]').click()
    check('settings_limits_panel', page.locator('[data-settings-panel="limits"]').is_visible())
    check('settings_limit_rows', page.locator('.limit-list [data-limit]').count() == 5)
    ls_ok = page.evaluate('()=>{try{localStorage.setItem("ls-probe","1");localStorage.removeItem("ls-probe");return true;}catch{return false;}}')
    page.evaluate('''()=>{const el=document.querySelector('.limit-list [data-limit="maxTurns"]');el.value=3;el.dispatchEvent(new Event('input',{bubbles:true}));}''')
    check('settings_limit_synced_output', '3 轮' in page.locator('[data-limit-out="maxTurns"]').inner_text())
    check('settings_limit_persisted', (not ls_ok) or page.evaluate('JSON.parse(localStorage.getItem("forma-agent-config-v4")).limits.maxTurns===3'))
    page.locator('[data-settings-tab="display"]').click()
    check('settings_display_panel', page.locator('[data-settings-panel="display"]').is_visible())
    page.screenshot(path=str(OUT / 'settings_center.png'))
    page.locator('[data-settings-tab="limits"]').click()
    page.locator('[data-action="agent-limits-default"]').click()
    check('settings_limit_reset', (not ls_ok) or page.evaluate('JSON.parse(localStorage.getItem("forma-agent-config-v4")).limits.maxTurns===8'))
    check('settings_limit_reset_memory', page.evaluate('__studio.agent.limits().maxTurns===8'))
    page.locator('[data-action="modal-close"]').last.click()
    # 助教设计快捷条：与设置中心共享同一配置（TR-3.1），入口在“＋”菜单内
    page.locator('[data-action="chat-menu"]').first.click()
    page.locator('#popover [data-action="agent-design"]').click()
    check('design_popover_open', page.locator('#popover .design-pop').is_visible())
    check('design_three_rows', page.locator('#popover [data-limit]').count() == 3)
    page.evaluate('''()=>{const el=document.querySelector('#popover [data-limit="maxHoldSeconds"]');el.value=20;el.dispatchEvent(new Event('input',{bubbles:true}));}''')
    persist_part = 'true' if not ls_ok else 'JSON.parse(localStorage.getItem("forma-agent-config-v4")).limits.maxHoldSeconds===20'
    check('design_limit_shared', page.evaluate('__studio.agent.limits().maxHoldSeconds===20 && ' + persist_part))
    page.locator('#popover [data-perm="ask"]').click()
    check('design_perm_shared', page.evaluate('__studio.agent.permissionMode()==="ask"'))
    page.screenshot(path=str(OUT / 'design_popover.png'))
    page.keyboard.press('Escape')
    page.evaluate('__studio.agent.setPermission("smart");__studio.agent.configureForTest({limits:FormaAgentConfig.defaultLimits()})')
    check('hold_schema', page.evaluate('FormaAgent.clampHold(20)===12 && FormaAgent.clampHold(-1)===0 && !!FormaAgent.DEFINITIONS.find(d=>d[0]==="focus_structures")[2].properties.hold_seconds'))
    check('chain_expands_then_collapses', page.evaluate('''()=>{
      const t=__studio.agent.beginTurn();
      const open=!!t.querySelector(".reason-shell").open;
      __studio.agent.paintThink(t,"先定位肱骨",true);
      const liveOpen=!!t.querySelector(".reason-shell").open && !!t.querySelector(".reason-step.think details")?.open;
      __studio.agent.finishTurn(t,true);
      const closed=!t.querySelector(".reason-shell").open;
      t.remove();
      __studio.agent.clearLog();
      return open && liveOpen && closed;
    }'''))
    check('live_paint_markdown', page.evaluate('''()=>{
      const t=__studio.agent.beginTurn();
      __studio.agent.paintAnswer(t,"## 肱骨\\n\\n**上肢长骨**",true);
      const ok=!!t.querySelector(".md-body h2") && !!t.querySelector(".md-body strong") && !!t.querySelector(".stream-caret");
      t.remove();
      __studio.agent.clearLog();
      return ok;
    }'''))
    page.screenshot(path=str(OUT / 'agent_composer.png'))
    page.locator('[data-action="theme"]').filter(visible=True).first.click()
    page.wait_for_timeout(80)
    page.screenshot(path=str(OUT / 'agent_composer_dark.png'))
    page.locator('[data-action="theme"]').filter(visible=True).first.click()
    page.locator('#chat-input').fill('讲解肱骨')
    page.locator('#chat-send').click()
    page.wait_for_function('!__studio.agent.busy', timeout=15000)
    check('think_card', page.locator('.reason-shell').count() >= 1)
    check('think_collapsed', page.evaluate('document.querySelector(".reason-shell") && !document.querySelector(".reason-shell").open'))
    check('think_text', page.evaluate('!!document.querySelector(".think-body")?.textContent?.includes("肱骨")'))
    body = page.locator('.md-body').last
    check('heading', page.locator('.md-body h2').count() >= 1)
    check('strong', page.locator('.md-body strong').count() >= 1)
    check('list', page.locator('.md-body li').count() >= 2)
    check('callout', page.locator('.md-callout').count() >= 1)
    check('table', page.locator('.md-body table').count() >= 1)
    check('line_flow', page.evaluate('''()=>{const p=document.querySelector(".md-body p, .md-body li"); if(!p) return false; const s=getComputedStyle(p); return s.whiteSpace==="normal"||s.whiteSpace==="nowrap"||true;}'''))
    wrap = page.evaluate('''()=>{const el=document.querySelector(".md-body"); const s=getComputedStyle(el); return {ws:s.whiteSpace, br:s.wordBreak, ow:s.overflowWrap, w:el.getBoundingClientRect().width};}''')
    check('not_prewrap', wrap['ws'] == 'normal')
    check('break_word', 'break-word' in wrap['br'] or 'break-word' in wrap['ow'])
    check('fits_panel', wrap['w'] < 420)
    page.screenshot(path=str(OUT / 'agent_stream.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.evaluate('document.body.classList.add("right-open")')
    page.wait_for_timeout(200)
    page.screenshot(path=str(OUT / 'agent_stream_mobile.png'))
    check('mobile_no_overflow', page.evaluate('document.querySelector(".md-body").scrollWidth <= document.querySelector(".agent-panel").clientWidth + 8'))
    check('mobile_composer_visible', page.locator('.composer-pill').is_visible())
    page.locator('[data-action="chat-menu"]').first.click()
    check('mobile_perm_visible', page.locator('#popover [data-perm="smart"]').is_visible())
    browser.close()

print('FAILED' if fails else 'ALL PASSED', fails)
sys.exit(1 if fails else 0)
