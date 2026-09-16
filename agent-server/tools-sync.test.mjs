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
 assert.deepEqual(writes,new Set(['focus_structures','isolate_structures','highlight_structures','set_layer','set_explode','set_view','start_practice']));
});
