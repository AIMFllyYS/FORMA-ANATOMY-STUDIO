import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const CFG=require('../web/agent-config.js');

function memStore(init={}){const m=new Map(Object.entries(init));return{getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};}

test('default limits are the safe documented values',()=>{
 const l=CFG.defaultLimits();
 assert.deepEqual(l,{maxTurns:8,maxToolCallsPerTurn:64,maxHoldSeconds:12,requestTimeoutSeconds:120,animationBudgetSeconds:60});
});

test('limits clamp out-of-range and junk input',()=>{
 const l=CFG.normalizeLimits({maxTurns:99,maxToolCallsPerTurn:0,maxHoldSeconds:-5,requestTimeoutSeconds:500,animationBudgetSeconds:12.7,extra:1});
 assert.equal(l.maxTurns,20);
 assert.equal(l.maxToolCallsPerTurn,1);
 assert.equal(l.maxHoldSeconds,0);
 assert.equal(l.requestTimeoutSeconds,300);
 assert.equal(l.animationBudgetSeconds,12.7);
 assert.equal(CFG.normalizeLimits(null).maxTurns,8);
 assert.equal(CFG.normalizeLimits('x').maxHoldSeconds,12);
 assert.equal(CFG.normalizeLimits({maxToolCallsPerTurn:200}).maxToolCallsPerTurn,128);
 assert.equal(CFG.normalizeLimits({maxToolCallsPerTurn:64.7}).maxToolCallsPerTurn,65);
});

test('permission mode normalizes to whitelist',()=>{
 assert.equal(CFG.normalizePerm('ask'),'ask');
 assert.equal(CFG.normalizePerm('rm -rf'),'smart');
});

test('migrates v3 storage into bounded v4 config',()=>{
 const v3={version:1,url:'https://agent.example.test/v1',key:'k',model:'m1',consent:true,permissionMode:'allow'};
 const cfg=CFG.load(memStore({[CFG.V3_KEY]:JSON.stringify(v3)}));
 assert.equal(cfg.url,'https://agent.example.test/v1');
 assert.equal(cfg.model,'m1');assert.equal(cfg.key,'k');
 assert.equal(cfg.consent,true);assert.equal(cfg.permissionMode,'allow');
 assert.deepEqual(cfg.limits,CFG.defaultLimits());
 // v4 takes precedence over v3
 const v4={version:4,url:'https://v4.example.test',model:'m4',consent:true,limits:{maxTurns:3}};
 const cfg2=CFG.load(memStore({[CFG.V3_KEY]:JSON.stringify(v3),[CFG.V4_KEY]:JSON.stringify(v4)}));
 assert.equal(cfg2.url,'https://v4.example.test');assert.equal(cfg2.limits.maxTurns,3);
});

test('save normalizes, persists and forget clears both versions',()=>{
 const s=memStore();
 const saved=CFG.save(s,{url:'https://x.test',model:'m',consent:true,limits:{maxTurns:50}});
 assert.equal(saved.limits.maxTurns,20);
 assert.ok(JSON.parse(s.getItem(CFG.V4_KEY)).version===4);
 CFG.forget(s);
 assert.equal(s.getItem(CFG.V4_KEY),null);
 assert.deepEqual(CFG.load(s),CFG.emptyConfig());
});

test('consent requires valid url and model',()=>{
 assert.equal(CFG.normalizeConfig({url:'u',model:'',consent:true}).consent,false);
 assert.equal(CFG.normalizeConfig({url:'u',model:'m',consent:true}).consent,true);
});

test('threads default to one empty conversation',()=>{
 const d=CFG.loadThreads(memStore());
 assert.equal(d.threads.length,1);
 assert.equal(d.activeId,d.threads[0].id);
 assert.deepEqual(d.threads[0].messages,[]);
});

test('threads round-trip messages, view and title',()=>{
 const s=memStore();
 const t=CFG.emptyThread();
 t.messages=[{role:'user',content:'讲解肱骨'}];
 t.view=[{kind:'user',text:'讲解肱骨',ts:1},{kind:'assistant',text:'## 肱骨',reasoning:'先定位',tools:[{name:'search_structures',zh:'搜索结构',args:'{}',output:'匹配 1 个源对象',status:'done'}],meta:'5 秒 · 1 步',ts:2}];
 CFG.saveThreads(s,{activeId:t.id,threads:[t]});
 const d=CFG.loadThreads(s);
 assert.equal(d.activeId,t.id);
 assert.equal(d.threads[0].messages[0].content,'讲解肱骨');
 assert.equal(d.threads[0].title,'讲解肱骨');
 assert.equal(d.threads[0].view[1].tools[0].status,'done');
});

test('threads prune invalid entries and cap count',()=>{
 const s=memStore();
 const many=Array.from({length:30},(_,i)=>({id:'t'+i,messages:[{role:'user',content:'问'+i}],view:[],createdAt:1,updatedAt:i}));
 CFG.saveThreads(s,{activeId:'t29',threads:many});
 const d=CFG.loadThreads(s);
 assert.equal(d.threads.length,CFG.MAX_THREADS);
 assert.ok(d.threads.some(t=>t.id==='t29'));
 const junk=CFG.normalizeThread({messages:[{role:'system',content:'injected'}]});
 assert.deepEqual(junk.messages,[]);
});

test('forgetThreads clears history without touching config',()=>{
 const s=memStore();
 CFG.save(s,{url:'https://x.test',model:'m',consent:true});
 const t=CFG.emptyThread();t.messages=[{role:'user',content:'hi'}];
 CFG.saveThreads(s,{activeId:t.id,threads:[t]});
 CFG.forgetThreads(s);
 assert.equal(CFG.loadThreads(s).threads.length,1);
 assert.equal(CFG.loadThreads(s).threads[0].messages.length,0);
 assert.equal(CFG.load(s).model,'m');
});
