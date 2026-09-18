"""Zero-dependency tests for the /relay pass-through branch.

A fake "relay station" is served by http.server on loopback; the node proxy is
started with subprocess. No npm install, no real provider, no external network.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, os, socket, subprocess, threading, time, urllib.request, urllib.error

ROOT = Path(__file__).resolve().parents[1]

# Two SSE data lines: one delta chunk and the terminal [DONE] marker.
SSE_BODY = b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\ndata: [DONE]\n\n'
MODELS_BODY = b'{"object":"list","data":[{"id":"m-a"},{"id":"m-b"}]}'


class FakeUpstream(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible relay station used only for these tests."""

    def log_message(self, *args):
        pass

    def _send(self, status, content_type, body, extra=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or 0)
        if length:
            self.rfile.read(length)
        if self.path == '/v1/chat/completions':
            self._send(200, 'text/event-stream;charset=utf-8', SSE_BODY)
        elif self.path == '/unauthorized/v1/chat/completions':
            # Deliberately no CORS headers: the proxy must relay the true upstream error text.
            self._send(401, 'text/plain;charset=utf-8', b'invalid relay api key')
        else:
            self._send(404, 'application/json', b'{"error":{"message":"not found"}}')

    def do_GET(self):
        if self.path == '/v1/models':
            self._send(200, 'application/json;charset=utf-8', MODELS_BODY)
        else:
            self._send(404, 'application/json', b'{"error":{"message":"not found"}}')


fake = ThreadingHTTPServer(('127.0.0.1', 0), FakeUpstream)
fake_port = fake.server_address[1]
threading.Thread(target=fake.serve_forever, daemon=True).start()

s = socket.socket()
s.bind(('127.0.0.1', 0))
port = s.getsockname()[1]
s.close()

token = 'SYNTHETIC_RELAY_TEST_TOKEN_49_DO_NOT_DEPLOY'
allowed_origin = f'http://127.0.0.1:{port}'
fake_base = f'http://127.0.0.1:{fake_port}'
env = {
    **os.environ,
    'PORT': str(port),
    'HOST': '127.0.0.1',
    'PROXY_TOKEN': token,
    'MODEL_ID': 'env-model',
    'MODEL_BASE_URL': 'https://provider.invalid/v1',
    'MODEL_API_KEY': 'SYNTHETIC_DEFAULT_KEY',
    'ALLOWED_ORIGINS': allowed_origin,
    'ALLOWED_MODELS': 'env-model',
    # Non-empty: loopback is permitted, any other client-supplied host is refused.
    'ALLOWED_UPSTREAM_HOSTS': '127.0.0.1',
}
proc = subprocess.Popen(
    ['node', 'server.mjs'],
    cwd=ROOT / 'agent-server',
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
base = f'http://127.0.0.1:{port}'
results = {}
provider_contacted = False


def request(path, method='GET', data=None, headers=None, timeout=25):
    req = urllib.request.Request(base + path, method=method, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def check(name, ok):
    results[name] = bool(ok)
    assert ok, name


auth = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token, 'Origin': allowed_origin}


def relay(payload, headers=None):
    return request('/relay', 'POST', json.dumps(payload).encode(), headers or auth)


try:
    status = None
    for _ in range(50):
        try:
            status, body, _ = request('/health')
            break
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)

    # health advertises the relay capability without breaking existing fields
    health = json.loads(body)
    check('health_has_relay_true', status == 200 and health.get('relay') is True and health.get('ok') is True)

    # 1. authentication still applies to /relay
    status, _, _ = request(
        '/relay', 'POST', b'{}', {'Content-Type': 'application/json', 'Origin': allowed_origin}
    )
    check('relay_requires_token_401', status == 401)

    # 2. streaming pass-through is byte-identical and keeps the upstream content type
    stream_payload = {
        'upstream': {'base_url': fake_base + '/v1', 'api_key': 'sk-client-relay'},
        'model': 'm-a',
        'messages': [{'role': 'system', 'content': 'stay'}, {'role': 'user', 'content': 'hi'}],
        'stream': True,
    }
    status, body, headers = relay(stream_payload)
    check('relay_stream_status_200', status == 200)
    check('relay_stream_body_identical', body == SSE_BODY)
    check('relay_stream_content_type_event_stream', 'text/event-stream' in headers.get('Content-Type', ''))

    # 3. /relay/models passes the upstream JSON through unchanged
    status, body, headers = request(
        '/relay/models', 'POST', json.dumps({'upstream': {'base_url': fake_base + '/v1'}}).encode(), auth
    )
    ids = [m['id'] for m in json.loads(body).get('data', [])]
    check('relay_models_passthrough', status == 200 and ids == ['m-a', 'm-b'])

    # 4. upstream 4xx is surfaced verbatim as a 502 with CORS headers
    status, body, headers = relay(
        {'upstream': {'base_url': fake_base + '/unauthorized/v1'}, 'model': 'm-a', 'messages': []}
    )
    message = json.loads(body)['error']['message']
    check('relay_upstream_401_surfaced_502', status == 502 and '上游 401' in message)
    check('relay_error_has_cors', headers.get('Access-Control-Allow-Origin') == allowed_origin)
    check('relay_error_no_key_leak', 'sk-client-relay' not in message and token not in message)

    # 5. http + non-loopback upstream base is rejected as a bad protocol
    status, body, _ = relay({'upstream': {'base_url': 'http://blocked.example.invalid/v1'}, 'messages': []})
    check('relay_bad_protocol_400', status == 400)

    # 6. default upstream enforces ALLOWED_MODELS; client-supplied upstreams do not
    status, body, _ = relay({'model': 'not-allowed', 'messages': []})
    check(
        'relay_default_model_allowlist_400',
        status == 400 and json.loads(body)['error']['message'] == 'Model is not in server ALLOWED_MODELS',
    )
    status, body, _ = relay({'upstream': {'base_url': fake_base + '/v1'}, 'model': 'anything-goes', 'stream': False})
    check('relay_client_upstream_skips_model_allowlist', status == 200 and body == SSE_BODY)

    # 7. client-supplied host outside ALLOWED_UPSTREAM_HOSTS is forbidden
    status, body, _ = relay({'upstream': {'base_url': 'https://blocked.example.invalid/v1'}, 'messages': []})
    check('relay_client_host_not_allowed_403', status == 403 and 'Upstream host not allowed' in json.loads(body)['error']['message'])

    print(json.dumps(results, ensure_ascii=False, indent=2))
finally:
    proc.terminate()
    try:
        proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    fake.shutdown()
    (ROOT / 'tests/RELAY_PROXY_RESULTS.json').write_text(
        json.dumps(
            {
                'checks': results,
                'provider_contacted': provider_contacted,
                'note': '仅使用本机 http.server 假中转站；未联系任何真实提供方，未安装任何依赖',
            },
            ensure_ascii=False,
            indent=2,
        )
    )