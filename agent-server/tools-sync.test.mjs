import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import {ALLOWED_NAMES} from './protocol.mjs';

const HERE=dirname(fileURLToPath(import.meta.url));
const SHARED=resolve(HERE,'../web/agent-tools.json');
const manifest=JSON.parse(readFileSync(SHARED,'utf8'));
const tools=manifest.tools;

test('shared tool manifest is the single source of truth',()=>{
 assert.ok(Array.isArray(tools)&&tools.length>=10,'清单至少包含现有 10 个工具');
 assert.equal(existsSync(resolve(HERE,'tool-definitions.json')),false,'旧的服务端重复定义文件应已删除');
 const names=tools.map(t=>t.name);
 assert.equal(new Set(names).size,names.length,'工具名唯一');
 assert.deepEqual(new Set(names),ALLOWED_NAMES,'协议白名单与共享清单完全一致');
});

test('every tool carries complete, bounded metadata',()=>{
 for(const t of tools){
  assert.match(t.name,/^[a-z][a-z0-9_]*$/,`合法工具名: ${t.name}`);
  assert.equal(typeof t.description,'string');assert.ok(t.description.length>=8,`描述非空: ${t.name}`);
  assert.equal(typeof t.mutatesCanvas,'boolean',`读写标记为布尔: ${t.name}`);
  assert.equal(typeof t.zh,'string');assert.ok(t.zh.length,`中文名: ${t.name}`);
  assert.equal(typeof t.icon,'string');assert.ok(t.icon.length,`图标: ${t.name}`);
  const s=t.parameters;
  assert.equal(s.type,'object',`${t.name}: 根 schema 为 object`);
  assert.equal(s.additionalProperties,false,`${t.name}: 拒绝额外字段`);
  assert.ok(s.properties&&typeof s.properties==='object',`${t.name}: 有 properties`);
  for(const r of s.required||[])assert.ok(Object.hasOwn(s.properties,r),`${t.name}: required 字段已定义: ${r}`);
  for(const [k,p] of Object.entries(s.properties)){
   assert.ok(p.type,`${t.name}.${k}: 声明类型`);
   if(p.type==='array'){assert.ok(p.items&&p.items.type,`${t.name}.${k}: 数组声明 items 类型`);}
   if(p.minimum!==undefined&&p.maximum!==undefined)assert.ok(p.minimum<=p.maximum,`${t.name}.${k}: 数值区间合法`);
   if(p.minItems!==undefined&&p.maxItems!==undefined)assert.ok(p.minItems<=p.maxItems,`${t.name}.${k}: 数量区间合法`);
  }
 }
});

test('read/write split matches the approval policy',()=>{
 const writes=new Set(tools.filter(t=>t.mutatesCanvas).map(t=>t.name));
 assert.deepEqual(writes,new Set(['focus_structures','isolate_structures','highlight_structures','set_layer','set_explode','toggle_structure_visibility','add_canvas_annotation','clear_canvas_annotations','set_view','start_practice','set_highlight','play_assembly','play_joint_motion','camera_tour','stop_animation']));
 // All write tools must be listed as read-write; the new read tools are read-only.
 assert.equal(tools.find(t=>t.name==='list_taxonomy').mutatesCanvas,false);
 assert.equal(tools.find(t=>t.name==='get_lesson').mutatesCanvas,false);
 assert.equal(tools.find(t=>t.name==='capture_current_canvas').mutatesCanvas,false,'画布截图是只读操作');
 assert.equal(tools.find(t=>t.name==='stop_animation').mutatesCanvas,true);
});

test('new teaching tools declare bounded, schema-valid parameters',()=>{
 const by=Object.fromEntries(tools.map(t=>[t.name,t]));
 for(const name of ['toggle_structure_visibility','add_canvas_annotation','clear_canvas_annotations','capture_current_canvas']){
  assert.ok(by[name],`工具存在: ${name}`);
  assert.equal(by[name].parameters.additionalProperties,false,`${name} 拒绝额外字段`);
 }
 const vis=by.toggle_structure_visibility.parameters;
 assert.equal(vis.properties.visible.type,'boolean');
 assert.ok(vis.properties.ids.items.type==='integer');
 assert.ok(vis.properties.duration_seconds===undefined||vis.properties.duration_seconds.type==='number');
 const anno=by.add_canvas_annotation.parameters;
 assert.ok(anno.required.includes('text'),'标注文本必填');
 assert.equal(anno.properties.text.type,'string');
 assert.ok((anno.properties.text.maxLength||0)>=40,'标注文本有合理上限');
 assert.equal(anno.properties.position.enum!==undefined,true);
 assert.equal(by.set_explode.parameters.properties.ids.items.type,'integer','局部爆炸支持 ids');
 assert.equal(by.capture_current_canvas.parameters.properties!==undefined,true);
});

test('teaching animation tools declare bounded, schema-valid parameters',()=>{
 const by=Object.fromEntries(tools.map(t=>[t.name,t]));
 for(const name of ['set_highlight','play_assembly','play_joint_motion','camera_tour','stop_animation','list_taxonomy','get_lesson']){
  assert.ok(by[name],`工具存在: ${name}`);
  assert.equal(by[name].parameters.additionalProperties,false,`${name} 拒绝额外字段`);
 }
 assert.equal(by.set_highlight.parameters.properties.state.enum.join(','),'accent,series,contraction');
 assert.ok(by.play_joint_motion.parameters.required.includes('joint'));
 assert.ok(by.play_joint_motion.parameters.required.includes('motion'));
 assert.ok(by.camera_tour.parameters.properties.views.maxItems<=8);
});
