/* Pure agent configuration: bounded limits, defaults, v3→v4 migration.
 * No DOM/network access; storage is injected so the module is node-testable. MIT. */
(function(global){
'use strict';
const V3_KEY='forma-agent-config-v3';
const V4_KEY='forma-agent-config-v4';
const PERM_MODES=['smart','allow','ask'];
// 硬边界：即使用户配置越界也被钳制在这些区间内。
const LIMIT_SPECS={
 maxTurns:{min:1,max:20,def:8,int:true},
 maxToolCallsPerTurn:{min:1,max:12,def:6,int:true},
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
const api={V3_KEY,V4_KEY,PERM_MODES,LIMIT_SPECS,clampSpec,defaultLimits,normalizeLimits,
 normalizePerm,emptyConfig,normalizeConfig,migrateV3,load,save,forget};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
else global.FormaAgentConfig=api;
})(typeof globalThis!=='undefined'?globalThis:this);
