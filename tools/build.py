#!/usr/bin/env python3
"""Build Forma's self-contained HTML. No generated or substitute anatomy.
Only supplied GLB data or a prior HTML's data payload are embedded.
Python 3.10+, standard library; Blender is optional for source export.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, re, shutil, struct, subprocess
from pathlib import Path
from html.parser import HTMLParser
ROOT = Path(__file__).resolve().parents[1]

class PayloadParser(HTMLParser):
    def __init__(self): super().__init__(); self.active=False; self.chunks=[]
    def handle_starttag(self, tag, attrs):
        if tag=='script' and dict(attrs).get('id')=='payload-data': self.active=True
    def handle_data(self, data):
        if self.active: self.chunks.append(data)
    def handle_endtag(self, tag):
        if tag=='script': self.active=False

def validate_glb(raw: bytes) -> dict:
    if len(raw)<28: raise ValueError('GLB too short')
    magic,version,length=struct.unpack_from('<III',raw)
    if (magic,version,length)!=(0x46546C67,2,len(raw)): raise ValueError('Invalid GLB header')
    off=12; gltf=None; found_bin=False
    while off+8<=len(raw):
        n,t=struct.unpack_from('<II',raw,off); off+=8
        if n%4 or off+n>len(raw): raise ValueError('Invalid chunk range')
        if t==0x4E4F534A: gltf=json.loads(raw[off:off+n].decode().rstrip('\x00 '))
        if t==0x004E4942: found_bin=True
        off+=n
    if off!=len(raw) or not gltf or not found_bin: raise ValueError('GLB JSON/BIN missing')
    if any(b.get('uri') for b in gltf.get('buffers',[])): raise ValueError('External buffers are not offline')
    unsupported={'KHR_draco_mesh_compression','EXT_meshopt_compression'}
    if unsupported.intersection(gltf.get('extensionsUsed',[])): raise ValueError('Compressed geometry is not supported; export uncompressed GLB')
    if gltf.get('skins') or any('skin' in n for n in gltf.get('nodes',[])): raise ValueError('Bake skin deformation before export')
    for m in gltf.get('meshes',[]):
        for p in m.get('primitives',[]):
            if p.get('mode',4)!=4 or p.get('targets'): raise ValueError('Only static triangles are supported')
    return gltf

def clean_payload(pack: dict) -> dict:
    # Explicit allowlist: never propagate HTML, scripts, API credentials or chats.
    out={k:pack[k] for k in ('notes','patches','favorites','quizHistory','views','view','theme') if k in pack}
    out.update(version=3,assets=[])
    for a in pack.get('assets',[]):
        allowed=('id','filename','category','sha256','origin','quality','license','attribution','sourceURL','source','extras','annotations','objects','triangles','bytes','loadedAt')
        raw=base64.b64decode(a['data'],validate=True)
        if len(raw)>750*1024**2: raise ValueError('Asset over 750 MB')
        if a.get('filename','').lower().endswith('.glb'): validate_glb(raw)
        hash_=hashlib.sha256(raw).hexdigest()
        if a.get('sha256') and hash_!=a['sha256']: raise ValueError('SHA-256 mismatch')
        meta={k:a[k] for k in allowed if k in a}
        out['assets'].append({**meta,'sha256':hash_,'bytes':len(raw),'embedded':True,'data':a['data']})
    return out

def build(output: Path, pack: dict | None=None):
    pack=clean_payload(pack or {})
    template=(ROOT/'web/shell.html').read_text(encoding='utf-8')
    values={'/*STYLE*/':(ROOT/'web/style.css').read_text(), '<!--ICONS-->':(ROOT/'web/icons.svg').read_text(),
      '/*KNOWLEDGE*/':json.dumps(json.loads((ROOT/'web/knowledge.json').read_text()),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c'),
      '/*AGENT_TOOLS*/':json.dumps(json.loads((ROOT/'web/agent-tools.json').read_text()),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')}
    for marker,name in [('/*ENGINE*/','mesh-engine.js'),('/*CORE*/','core.js'),('/*PINYIN*/','pinyin-data.js'),('/*KNOWLEDGE_LOGIC*/','knowledge.js'),('/*MARKDOWN*/','markdown.js'),('/*AGENT*/','agent.js'),('/*APP*/','app.js')]:
        values[marker]=(ROOT/'web'/name).read_text().replace('</script','<\\/script')
    for marker,value in values.items():
        if marker not in template: raise ValueError('Missing build marker '+marker)
        template=template.replace(marker,value)
    payload=json.dumps(pack,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    template=re.sub(r'<!--ASSET_PAYLOAD_BEGIN-->.*?<!--ASSET_PAYLOAD_END-->',lambda _: '<!--ASSET_PAYLOAD_BEGIN--><script id="payload-data" type="application/json">'+payload+'</script><!--ASSET_PAYLOAD_END-->',template,count=1,flags=re.S)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(template,encoding='utf-8')
    report={'file':str(output.name),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'embedded_assets':[{'filename':a.get('filename'),'sha256':a['sha256'],'bytes':a['bytes']} for a in pack['assets']],'anatomical_review':'NOT_PERFORMED','key_or_chat_included':False}
    output.with_suffix('.build.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(f'Built {output} ({report["bytes"]:,} bytes, {len(pack["assets"])} embedded assets)')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'dist/forma_anatomy_studio.html')
    p.add_argument('--input-dir',type=Path,help='GLB directory, optional manifest.json')
    p.add_argument('--from-html',type=Path,help='Import payload only from previous offline HTML')
    p.add_argument('--blend',type=Path,help='Original .blend; no auto-execution of source scripts')
    p.add_argument('--blender',default=shutil.which('blender'))
    p.add_argument('--systems',default='skeletal,joints,muscles,nerves')
    a=p.parse_args();pack={}
    if a.blend:
        if not a.blender: p.error('Blender unavailable. No lower-quality fallback is substituted.')
        out=ROOT/'models/source-export';out.mkdir(parents=True,exist_ok=True)
        subprocess.run([str(a.blender),'--factory-startup','--disable-autoexec','--background',str(a.blend.resolve()),'--python-exit-code','2','--python',str(ROOT/'tools/export_blender.py'),'--','--output',str(out),'--systems',a.systems],check=True)
        a.input_dir=out
    if a.from_html:
        parser=PayloadParser();parser.feed(a.from_html.read_text(encoding='utf-8'));pack=json.loads(''.join(parser.chunks))
        if not pack.get('assets'): p.error('This HTML is a launcher without embedded assets.')
    if a.input_dir:
        manifest={};mf=a.input_dir/'manifest.json'
        if mf.exists():manifest=json.loads(mf.read_text())
        metas={x['filename']:x for x in manifest.get('assets',[])}
        pack.setdefault('assets',[])
        for f in sorted(a.input_dir.glob('*.glb')):
            raw=f.read_bytes();validate_glb(raw);meta=metas.get(f.name,{})
            pack['assets'].append({**meta,'filename':f.name,'category':meta.get('category','other'),'data':base64.b64encode(raw).decode()})
        if not pack['assets']:p.error('No real GLB assets found. No substitutes generated.')
    build(a.output,pack)
if __name__=='__main__':main()
