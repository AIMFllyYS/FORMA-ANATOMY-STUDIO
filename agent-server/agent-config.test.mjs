import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const CFG=require('../web/agent-config.js');

function memStore(init={}){const m=new Map(Object.entries(init));return{getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};}

test('default limits are the safe documented values',()=>{
 const l=CFG.defaultLimits();
 assert.deepEqual(l,{maxTurns:8,maxToolCallsPerTurn:6,maxHoldSeconds:12,requestTimeoutSeconds:120,animationBudgetSeconds:60});
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
