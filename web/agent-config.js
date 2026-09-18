/* Pure agent configuration: bounded limits, defaults, v3→v5 migration.
 * No DOM/network access; storage is injected so the module is node-testable. MIT. */
(function(global){
'use strict';
const V3_KEY='forma-agent-config-v3';
// 存储键沿用 v4 名称以保数据连续；结构自 v5 起为「多配置档 + 连接方式」，
// 旧结构（扁平 url/key/model）在 normalizeConfig 里就地升级，无需换键。
const V4_KEY='forma-agent-config-v4';
const CONFIG_VERSION=5;
const THREAD_KEY='forma-agent-threads-v1';
const PERM_MODES=['smart','allow','ask'];
const PERM_ZH={smart:'智能批准',allow:'所有权限',ask:'请求批准'};
// 连接方式：auto 本机代理优先、失败回退浏览器直连；relay 只用本机代理；direct 只浏览器直连。
const MODES=['auto','relay','direct'];
const MODE_ZH={auto:'自动 · 代理优先',relay:'仅本机代理',direct:'仅浏览器直连'};
const MODE_HINT={
 auto:'先走本机代理（同源、无跨域，上游错误原样显示）；代理未启动时自动回退浏览器直连。',
 relay:'只经本机代理，浏览器不直连任何外部地址。代理未启动时会直接报错。',
 direct:'浏览器直连接口地址，需要服务端放行 CORS，错误原因会被浏览器隐去。'
};
// 本机代理默认入口（agent-server：npm start 后 http://127.0.0.1:8787/relay）。
const DEFAULT_RELAY_URL='http://127.0.0.1:8787/relay';
const MAX_PROFILES=8;
const MAX_MODELS_PER_PROFILE=48;
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
function str(v,n){return typeof v==='string'?v.slice(0,n):'';}
function normalizeMode(m){return MODES.includes(m)?m:'auto';}
// 配置档 = 一个接口 URL + 一组可选模型 + 当前模型。id 由序号派生，保证空配置可深比较。
function defaultProfile(i=0){return{id:'p'+(i+1),name:i?'配置 '+(i+1):'默认配置',url:'',key:'',models:[],model:''};}
function normalizeModels(raw,model){
 const out=[];
 for(const m of Array.isArray(raw)?raw:[]){const s=str(m,200).trim();if(s&&!out.includes(s))out.push(s);}
 if(model&&!out.includes(model))out.unshift(model);
 return out.slice(0,MAX_MODELS_PER_PROFILE);
}
function normalizeProfile(raw,i){
 const base=defaultProfile(i);
 if(!raw||typeof raw!=='object')return base;
 const id=typeof raw.id==='string'&&/^[A-Za-z0-9_-]{1,24}$/.test(raw.id)?raw.id:base.id;
 const model=str(raw.model,200).trim();
 return{id,name:str(raw.name,40).trim()||base.name,url:str(raw.url,400).trim(),key:str(raw.key,8000),
  models:normalizeModels(raw.models,model),model};
}
function nextProfileId(profiles){let n=0;for(const p of profiles||[]){const m=/^p(\d+)$/.exec(p?.id||'');if(m)n=Math.max(n,Number(m[1]));}return'p'+(n+1);}
function newProfile(profiles,url=''){const list=profiles||[];return{...defaultProfile(list.length),id:nextProfileId(list),name:'配置 '+(list.length+1),url};}
function emptyConfig(){return{url:'',key:'',model:'',profiles:[defaultProfile(0)],activeProfile:'p1',
 mode:'auto',relayUrl:DEFAULT_RELAY_URL,relayToken:'',
 consent:false,vision:false,permissionMode:'smart',limits:defaultLimits()};}
function normalizeConfig(raw){
 if(!raw||typeof raw!=='object')return emptyConfig();
 const mode=normalizeMode(raw.mode);
 // 有 profiles 就用它；只有旧结构（扁平 url/key/model）时把扁平字段升级成第一个配置档。
 const src=Array.isArray(raw.profiles)&&raw.profiles.length?raw.profiles:[raw];
 const profiles=src.slice(0,MAX_PROFILES).map((p,i)=>normalizeProfile(p,i));
 let activeProfile=typeof raw.activeProfile==='string'?raw.activeProfile:'';
 if(!profiles.some(p=>p.id===activeProfile))activeProfile=profiles[0].id;
 const act=profiles.find(p=>p.id===activeProfile)||profiles[0];
 // url/key/model 是活动配置档的只读投影：旧读取方（v4 结构与其他模块）读它们即可，
 // 写入方向恒为 profiles → 投影，避免两份真相漂移。
 const url=act.url,model=act.model,key=act.key;
 return{url,key,model,profiles,activeProfile,mode,
  relayUrl:str(raw.relayUrl,400).trim()||DEFAULT_RELAY_URL,relayToken:str(raw.relayToken,8000),
  // 走代理时不再要求浏览器侧 URL（可只填模型，由服务端 .env 决定上游）。
  consent:raw.consent===true&&!!model&&(mode==='direct'?!!url:true),
  // vision：用户显式声明当前模型支持图像输入时才把画布截图作为 image_url 发送。
  vision:raw.vision===true,
  permissionMode:normalizePerm(raw.permissionMode),limits:normalizeLimits(raw.limits)};
}
// v3 结构：{version:1,url,key,model,consent,permissionMode}
function migrateV3(raw){
 const base=emptyConfig();
 if(!raw||typeof raw!=='object')return base;
 const one=normalizeProfile({...base.profiles[0],url:raw.url,key:raw.key,model:raw.model,models:[raw.model]},0);
 return normalizeConfig({...base,profiles:[one],activeProfile:one.id,
  consent:raw.consent===true,permissionMode:normalizePerm(raw.permissionMode)});
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
 try{storage.setItem(V4_KEY,JSON.stringify({version:CONFIG_VERSION,...n}));}catch{return null;}
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
 if(role==='tool'){
  // 多模态截图工具消息（content 为 part 数组）落盘时只保留文字部分，base64 不入 localStorage。
  let c=m.content;
  if(Array.isArray(c))c=c.map(p=>p?.type==='text'?p.text:'').filter(Boolean).join('\n');
  return{role:'tool',tool_call_id:String(m.tool_call_id||'').slice(0,80),content:String(c??'').slice(0,8000)};
 }
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
const api={V3_KEY,V4_KEY,CONFIG_VERSION,THREAD_KEY,PERM_MODES,PERM_ZH,MODES,MODE_ZH,MODE_HINT,DEFAULT_RELAY_URL,MAX_PROFILES,MAX_MODELS_PER_PROFILE,
 MAX_THREADS,MAX_MSGS_PER_THREAD,MAX_VIEW_TURNS,LIMIT_SPECS,clampSpec,defaultLimits,normalizeLimits,
 normalizePerm,normalizeMode,defaultProfile,normalizeProfile,newProfile,emptyConfig,normalizeConfig,migrateV3,load,save,forget,threadId,emptyThread,emptyThreads,normalizeThread,normalizeMsg,normalizeViewTurn,threadTitle,loadThreads,saveThreads,forgetThreads};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
else global.FormaAgentConfig=api;
})(typeof globalThis!=='undefined'?globalThis:this);
