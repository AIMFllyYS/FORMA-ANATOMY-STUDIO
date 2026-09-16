"""Packaging regression tests. Fixtures are synthetic graphics, never anatomy."""
import base64, hashlib, importlib.util, json, re, struct, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from fixture import glb
spec=importlib.util.spec_from_file_location('build',ROOT/'tools/build.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

def mutate(raw,fn):
 n=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+n]);fn(doc)
 text=json.dumps(doc,separators=(',',':')).encode();text+=b' '*((-len(text))%4)
 rest=raw[20+n:]
 return struct.pack('<III',0x46546C67,2,20+len(text)+len(rest))+struct.pack('<II',len(text),0x4E4F534A)+text+rest
class BuildTests(unittest.TestCase):
 def test_glb_fixture_parses(self):self.assertEqual(sum('mesh' in n for n in build.validate_glb(glb())['nodes']),9)
 def test_invalid_header_rejected(self):
  with self.assertRaises(ValueError):build.validate_glb(b'INVALID_HEADER'+glb()[14:])
 def test_external_buffer_rejected(self):
  with self.assertRaises(ValueError):build.validate_glb(mutate(glb(),lambda d:d['buffers'][0].update(uri='https://example.invalid/data.bin')))
 def test_draco_rejected(self):
  with self.assertRaises(ValueError):build.validate_glb(mutate(glb(),lambda d:d.update(extensionsUsed=['KHR_draco_mesh_compression'])))
 def test_skins_rejected(self):
  with self.assertRaises(ValueError):build.validate_glb(mutate(glb(),lambda d:d.update(skins=[{}])))
 def test_sha_mismatch_rejected(self):
  with self.assertRaises(ValueError):build.clean_payload({'assets':[{'filename':'TEST.glb','sha256':'0'*64,'data':base64.b64encode(glb()).decode()}]})
 def test_key_and_chat_not_propagated(self):
  cleaned=build.clean_payload({'notes':{},'apiKey':'SECRET_DO_NOT_PROPAGATE','agent':{'key':'x'},'chat':['private']})
  self.assertEqual(set(cleaned),{'notes','version','assets'})
 def test_inert_payload_parser(self):
  parser=build.PayloadParser();parser.feed('<script>throw Error("not executed")</script><script id="payload-data" type="application/json">{"assets":[]}</script>')
  self.assertEqual(json.loads(''.join(parser.chunks)),{'assets':[]})
 def test_offline_pack_preserves_exact_bytes(self):
  raw=glb();pack={'assets':[{'filename':'TEST_ONLY_NOT_ANATOMY.glb','data':base64.b64encode(raw).decode()}],'notes':{'safe':'</script><script>INERT_NOTE</script>'},'apiKey':'SECRET_DO_NOT_PROPAGATE'}
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/'TEST_ONLY.html';report=build.build(f,pack);html=f.read_text();p=build.PayloadParser();p.feed(html);restored=json.loads(''.join(p.chunks))
   self.assertEqual(base64.b64decode(restored['assets'][0]['data']),raw)
   self.assertEqual(restored['assets'][0]['sha256'],hashlib.sha256(raw).hexdigest())
   self.assertNotIn('SECRET_DO_NOT_PROPAGATE',html)
   self.assertNotIn('</script><script>INERT_NOTE',html)
   self.assertEqual(restored['notes'],pack['notes']);self.assertEqual(len(report['embedded_assets']),1)
 def test_shipping_launcher_has_no_test_mesh(self):
  html=(ROOT/'dist/forma_anatomy_studio.html').read_text();parser=build.PayloadParser();parser.feed(html)
  self.assertEqual(json.loads(''.join(parser.chunks))['assets'],[])
  self.assertNotRegex(html,r'<script[^>]+src=')
  self.assertNotIn('SYNTHETIC_GRAPHICS_NOT_ANATOMY',html)
 def test_compiled_html_includes_markdown_agent(self):
  html=(ROOT/'dist'/'forma_anatomy_studio.html').read_text(encoding='utf-8')
  self.assertIn('FormaMarkdown',html);self.assertIn('readSSE',html);self.assertIn('ktext-callout',html);self.assertIn('forma-agent-config-v3',html)
  self.assertIn('renderLive',html);self.assertIn('hold_seconds',html);self.assertIn('data-perm="smart"',html)
 def test_pinyin_table_is_compact_json(self):
  raw=(ROOT/'web'/'pinyin-data.js').read_text(encoding='utf-8')
  payload=json.loads(raw.split('window.FormaPinyin=',1)[1].rstrip().rstrip(';'))
  self.assertIn('肱骨',payload['phrase']);self.assertEqual(payload['phrase']['肱骨'],'gōng gǔ')
  self.assertEqual(payload['char']['椎'],'zhuī');self.assertEqual(payload['char']['肋'],'lèi')
if __name__=='__main__':unittest.main(verbosity=2)
