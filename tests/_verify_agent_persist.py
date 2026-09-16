"""Verify Agent API config persists in localStorage, not in records/export."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / 'dist' / 'forma_anatomy_studio.html').read_text(encoding='utf-8')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

def open_html(page):
    page.goto((ROOT / 'dist' / 'forma_anatomy_studio.html').as_uri() + '#no-auto')
    page.wait_for_function('window.__studio && window.FormaAgent')

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True)
    ctx = browser.new_context()
    page = ctx.new_page()
    open_html(page)
    page.locator('[data-action="agent-settings"]').filter(visible=True).first.click()
    page.locator('#agent-url').fill('https://agent.example.test/v1')
    page.locator('#agent-model').fill('keep-me')
    page.locator('#agent-key').fill('LOCAL_KEY_SHOULD_PERSIST')
    page.locator('#agent-consent').check()
    page.locator('[data-action="agent-save"]').click()
    page.wait_for_timeout(80)
    stored = page.evaluate('JSON.parse(localStorage.getItem("forma-agent-config-v3"))')
    assert stored['key'] == 'LOCAL_KEY_SHOULD_PERSIST', stored
    assert stored['model'] == 'keep-me'
    assert stored.get('permissionMode', 'smart') == 'smart'
    page2 = ctx.new_page()
    open_html(page2)
    restored = page2.evaluate('({model:__studio.agent.config.model,key:__studio.agent.config.key,consent:__studio.agent.config.consent,url:__studio.agent.config.url})')
    assert restored['key'] == 'LOCAL_KEY_SHOULD_PERSIST', restored
    assert restored['model'] == 'keep-me' and restored['consent'] is True
    pack = page2.evaluate('JSON.stringify(__studio.recordPack())')
    assert 'LOCAL_KEY_SHOULD_PERSIST' not in pack
    store = page2.evaluate('JSON.stringify(__studio.state)')
    assert 'LOCAL_KEY_SHOULD_PERSIST' not in store
    fresh = browser.new_context().new_page()
    open_html(fresh)
    assert fresh.evaluate('__studio.agent.config.key') == ''
    print('ALL PASSED', restored['url'])
    browser.close()
