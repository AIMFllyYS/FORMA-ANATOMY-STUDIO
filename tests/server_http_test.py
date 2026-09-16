"""Server routing/auth tests without installing SDK or contacting a provider."""
from pathlib import Path
import json, os, socket, subprocess, time, urllib.request, urllib.error
ROOT=Path(__file__).resolve().parents[1]
s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
token='SYNTHETIC_TEST_PROXY_TOKEN_49_DO_NOT_DEPLOY'
env={**os.environ,'PORT':str(port),'HOST':'127.0.0.1','PROXY_TOKEN':token,'MODEL_ID':'test-only','MODEL_BASE_URL':'https://provider.invalid/v1','MODEL_API_KEY':'SYNTHETIC_TEST_KEY','ALLOWED_ORIGINS':f'http://127.0.0.1:{port}'}
proc=subprocess.Popen(['node','server.mjs'],cwd=ROOT/'agent-server',env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
base=f'http://127.0.0.1:{port}';results={}
def request(path,method='GET',data=None,headers=None):
 req=urllib.request.Request(base+path,method=method,headers=headers or {},data=data)
 try:
  with urllib.request.urlopen(req,timeout=5) as r:return r.status,r.read(),dict(r.headers)
 except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
def check(name,ok):results[name]=bool(ok);assert ok,name
try:
 for _ in range(50):
  try:
   status,body,h=request('/health');break
  except (OSError,urllib.error.URLError):time.sleep(.1)
 check('health_route',status==200 and json.loads(body)['ok'])
 check('health_no_key',b'SYNTHETIC_TEST_KEY' not in body)
 status,body,h=request('/');check('serves_one_compiled_artifact',status==200 and b'Forma' in body)
 status,body,h=request('/../../.env');check('no_arbitrary_file_read',status==404)
 status,body,h=request('/agent','POST',b'{}',{'Content-Type':'application/json'});check('auth_required',status==401)
 status,body,h=request('/agent','POST',b'{}',{'Content-Type':'application/json','Authorization':'Bearer '+token,'Origin':'https://untrusted.invalid'});check('origin_rejected',status==403)
 status,body,h=request('/agent','POST',b'{"model":"not-allowed","messages":[]}',{'Content-Type':'application/json','Authorization':'Bearer '+token});check('model_allowlist',status==400)
 status,body,h=request('/agent','POST',b'{"messages":[{"role":"invalid","content":"x"}]}',{'Content-Type':'application/json','Authorization':'Bearer '+token});check('invalid_messages_rejected',status in (400,502))
 status,body,h=request('/agent','OPTIONS',headers={'Origin':base});check('explicit_cors_preflight',status==204 and h.get('Access-Control-Allow-Origin')==base)
 print(json.dumps(results,ensure_ascii=False,indent=2))
finally:
 proc.terminate();proc.communicate(timeout=5)
 (ROOT/'tests/SERVER_HTTP_RESULTS.json').write_text(json.dumps({'checks':results,'provider_contacted':False,'sdk_installed':False},ensure_ascii=False,indent=2))
