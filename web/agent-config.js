/* Pure agent configuration: bounded limits, defaults, v3→v4 migration.
 * No DOM/network access; storage is injected so the module is node-testable. MIT. */
(function(global){
'use strict';
const V3_KEY='forma-agent-config-v3';
const V4_KEY='forma-agent-config-v4';
const THREAD_KEY='forma-agent-threads-v1';
const PERM_MODES=['smart','allow','ask'];
const PERM_ZH={smart:'智能批准',allow:'所有权限',ask:'请求批准'};
// 对话线程只存本机，不进入学习记录与离线导出（构建器 payload 白名单天然排除）。
const MAX_THREADS=20;
const MAX_MSGS_PER_THREAD=100;
const MAX_VIEW_TURNS=60;
const MAX_TEXT_CHARS=20000;
// 硬边界：即使用户配置越界也被钳制在这些区间内。
const LIMIT_SPECS={
 maxTurns:{min:1,max:20,def:8,int:true},
 // 单轮工具数：教学场景每轮常需数十个并行工具调用，上限 128、默认 64；
 // 服务端代理取 max 作安全天花板（见 agent-server/protocol.mjs）。
 maxToolCallsPerTurn:{min:1,max:128,def:64,int:true},
 maxHoldSeconds:{min:0,max:60,def:12},
 requestTimeoutSeconds:{min:30,max:300,def:120,int:true},
 animationBudgetSeconds:{min:0,max:180,def:60}
};
function clampSpec(v,s){
 let n=Number(v);
 if(!Number.isFinite(n))n=s.def;
 if(s.int)n=Math.round(n);
 return Math.max(s.min,Math.min(s.max,n));
}
function defaultLimits(){const o={};for(const[k,s]of Object.entries(LIMIT_SPECS))o[k]=s.def;return o;}
function normalizeLimits(raw){
 const out=defaultLimits();const src=raw&&typeof raw==='object'?raw:{};
 for(const[k,s]of Object.entries(LIMIT_SPECS))if(src[k]!==undefined&&src[k]!==null)out[k]=clampSpec(src[k],s);
 return out;
}
function normalizePerm(m){return PERM_MODES.includes(m)?m:'smart';}
function emptyConfig(){return{url:'',key:'',model:'',consent:false,proxy:false,permissionMode:'smart',limits:defaultLimits()};}
function str(v,n){return typeof v==='string'?v.slice(0,n):'';}
function normalizeConfig(raw){
 if(!raw||typeof raw!=='object')return emptyConfig();
 const url=str(raw.url,400),model=str(raw.model,200),key=str(raw.key,8000);
 return{url,key,model,consent:raw.consent===true&&!!url&&!!model,proxy:false,
  permissionMode:normalizePerm(raw.permissionMode),limits:normalizeLimits(raw.limits)};
}
// v3 结构：{version:1,url,key,model,consent,permissionMode}
function migrateV3(raw){
 const base=emptyConfig();
 if(!raw||typeof raw!=='object')return base;
 return{...base,url:str(raw.url,400),key:str(raw.key,8000),model:str(raw.model,200),
  consent:raw.consent===true,permissionMode:normalizePerm(raw.permissionMode)};
}
function load(storage){
 let v4=null;
 try{const t=storage?.getItem?.(V4_KEY);if(t)v4=JSON.parse(t);}catch{v4=null;}
 if(v4)return normalizeConfig(v4);
 let v3=null;
 try{const t=storage?.getItem?.(V3_KEY);if(t)v3=JSON.parse(t);}catch{v3=null;}
 return migrateV3(v3);
}
function save(storage,cfg){
 const n=normalizeConfig(cfg);
 try{storage.setItem(V4_KEY,JSON.stringify({version:4,...n}));}catch{return null;}
 return n;
}
function forget(storage){try{storage.removeItem(V4_KEY);}catch{}try{storage.removeItem(V3_KEY);}catch{}}
function threadId(){try{if(globalThis.crypto?.randomUUID)return'ct-'+crypto.randomUUID().slice(0,8);}catch{}return'ct-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,7);}
function clipText(v,n){return typeof v==='string'?(v.length>n?v.slice(0,n):v):'';}
function normalizeMsg(m){
 if(!m||typeof m!=='object')return null;
 const role=m.role;
 if(role==='user'){const c=typeof m.content==='string'?m.content:'';if(!c)return null;return{role:'user',content:c.slice(0,MAX_TEXT_CHARS)};}
 if(role==='assistant'){
  const out={role:'assistant',content:m.content==null?null:String(m.content).slice(0,MAX_TEXT_CHARS)};
  if(Array.isArray(m.tool_calls))out.tool_calls=m.tool_calls.filter(t=>t&&t.type!==undefined).map(t=>({id:String(t.id||'').slice(0,80),type:'function',function:{name:String(t.function?.name||'').slice(0,80),arguments:String(typeof t.function?.arguments==='string'?t.function.arguments:JSON.stringify(t.function?.arguments||{})).slice(0,8000)}})).slice(0,12);
  return out;
 }
 if(role==='tool')return{role:'tool',tool_call_id:String(m.tool_call_id||'').slice(0,80),content:String(m.content??'').slice(0,8000)};
 return null;
}
function normalizeViewTurn(v){
 if(!v||typeof v!=='object')return null;
 if(v.kind==='user')return{kind:'user',text:clipText(v.text,MAX_TEXT_CHARS),ts:Number(v.ts)||0};
 if(v.kind==='error')return{kind:'error',text:clipText(v.text,4000),ts:Number(v.ts)||0};
 if(v.kind==='assistant'){
  const tools=Array.isArray(v.tools)?v.tools.slice(0,12).map(t=>({name:clipText(t.name,80),zh:clipText(t.zh||t.name,40),args:clipText(typeof t.args==='string'?t.args:JSON.stringify(t.args||{}),2000),output:clipText(typeof t.output==='string'?t.output:JSON.stringify(t.output??''),2000),status:clipText(t.status,16)})):[];
  return{kind:'assistant',text:clipText(v.text,MAX_TEXT_CHARS),reasoning:clipText(v.reasoning,8000),tools,meta:clipText(v.meta,200),ts:Number(v.ts)||0};
 }
 return null;
}
function threadTitle(t){
 const first=(t.messages||[]).find(m=>m.role==='user'&&m.content);
 if(first)return String(first.content).trim().split(/\n/)[0].slice(0,28)||'新的对话';
 return'新的对话';
}
function normalizeThread(t){
 if(!t||typeof t!=='object')return null;
 const id=typeof t.id==='string'&&t.id? t.id.slice(0,64):threadId();
 const messages=Array.isArray(t.messages)?t.messages.map(normalizeMsg).filter(Boolean).slice(-MAX_MSGS_PER_THREAD):[];
 const view=Array.isArray(t.view)?t.view.map(normalizeViewTurn).filter(Boolean).slice(-MAX_VIEW_TURNS):[];
 const createdAt=Number(t.createdAt)||Date.now(),updatedAt=Number(t.updatedAt)||createdAt;
 // 有消息时标题恒从首问派生，避免空标题线程残留“新的对话”；
 // 无消息时保留原标题（新建态）。
 const out={id,createdAt,updatedAt,messages,view,title:messages.length?threadTitle({messages}):(clipText(t.title,40)||'新的对话')};
 return out;
}
function emptyThread(){const now=Date.now();return{id:threadId(),title:'新的对话',createdAt:now,updatedAt:now,messages:[],view:[]};}
function emptyThreads(){const t=emptyThread();return{activeId:t.id,threads:[t]};}
function loadThreads(storage){
 try{
  const raw=storage?.getItem?.(THREAD_KEY);
  if(!raw)return emptyThreads();
  const data=JSON.parse(raw);
  const arr=Array.isArray(data)?data:Array.isArray(data?.threads)?data.threads:null;
  if(!arr)return emptyThreads();
  const threads=arr.map(normalizeThread).filter(Boolean).slice(0,MAX_THREADS);
  if(!threads.length)return emptyThreads();
  threads.sort((a,b)=>b.updatedAt-a.updatedAt);
  let activeId=typeof data?.activeId==='string'?data.activeId:threads[0].id;
  if(!threads.some(t=>t.id===activeId))activeId=threads[0].id;
  return{activeId,threads};
 }catch{return emptyThreads();}
}
function saveThreads(storage,data){
 try{
  const threads=(data?.threads||[]).map(normalizeThread).filter(Boolean)
   .sort((a,b)=>b.updatedAt-a.updatedAt).slice(0,MAX_THREADS);
  if(!threads.length)return null;
  let activeId=data?.activeId;
  if(!threads.some(t=>t.id===activeId))activeId=threads[0].id;
  const payload=JSON.stringify({version:1,activeId,threads});
  try{storage.setItem(THREAD_KEY,payload);}
  catch{
   // 配额不足时丢弃最旧一半再试一次，仍失败则放弃持久化（本次会话仍可用）。
   const half=threads.slice(0,Math.max(1,Math.floor(MAX_THREADS/2)));
   try{storage.setItem(THREAD_KEY,JSON.stringify({version:1,activeId:half.some(t=>t.id===activeId)?activeId:half[0].id,threads:half}));}catch{return null;}
  }
  return{activeId,threads};
 }catch{return null;}
}
function forgetThreads(storage){try{storage?.removeItem?.(THREAD_KEY);}catch{}}
const api={V3_KEY,V4_KEY,THREAD_KEY,PERM_MODES,PERM_ZH,MAX_THREADS,MAX_MSGS_PER_THREAD,MAX_VIEW_TURNS,LIMIT_SPECS,clampSpec,defaultLimits,normalizeLimits,
 normalizePerm,emptyConfig,normalizeConfig,migrateV3,load,save,forget,threadId,emptyThread,emptyThreads,normalizeThread,normalizeMsg,normalizeViewTurn,threadTitle,loadThreads,saveThreads,forgetThreads};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
else global.FormaAgentConfig=api;
})(typeof globalThis!=='undefined'?globalThis:this);
