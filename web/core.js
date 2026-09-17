/* Forma core: storage, provenance and asset ingestion. MIT. */
(()=>{
'use strict';
async function sha256(buffer){
 if(globalThis.crypto?.subtle){try{const d=await crypto.subtle.digest('SHA-256',buffer);return Array.from(new Uint8Array(d),b=>b.toString(16).padStart(2,'0')).join('');}catch(e){}}
 // SHA-256 fallback for local/in-memory origins without Web Crypto; no network.
 const K=new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
 const H=new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]),input=new Uint8Array(buffer),length=input.length,total=Math.ceil((length+9)/64)*64,W=new Uint32Array(64),block=new Uint8Array(64),dv=new DataView(block.buffer);const r=(v,n)=>(v>>>n)|(v<<(32-n));
 for(let offset=0;offset<total;offset+=64){block.fill(0);const n=Math.max(0,Math.min(64,length-offset));if(n)block.set(input.subarray(offset,offset+n));if(offset<=length&&length<offset+64)block[length-offset]=128;if(offset+64===total){dv.setUint32(56,Math.floor(length/536870912),false);dv.setUint32(60,(length*8)>>>0,false);}for(let j=0;j<16;j++)W[j]=dv.getUint32(j*4,false);for(let j=16;j<64;j++){const a=W[j-15],b=W[j-2],s0=r(a,7)^r(a,18)^(a>>>3),s1=r(b,17)^r(b,19)^(b>>>10);W[j]=(W[j-16]+s0+W[j-7]+s1)>>>0;}let[a,b,c,d,e,f,g,h]=H;for(let j=0;j<64;j++){const s1=r(e,6)^r(e,11)^r(e,25),ch=(e&f)^(~e&g),t1=(h+s1+ch+K[j]+W[j])>>>0,s0=r(a,2)^r(a,13)^r(a,22),maj=(a&b)^(a&c)^(b&c),t2=(s0+maj)>>>0;h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;}for(const [j,v] of [a,b,c,d,e,f,g,h].entries())H[j]=(H[j]+v)>>>0;if(offset&&offset%524288===0)await tick();}
 return Array.from(H,x=>x.toString(16).padStart(8,'0')).join('');
}
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon=name=>`<svg class="ico" aria-hidden="true"><use href="#i-${esc(name)}"/></svg>`;
const tick=()=>new Promise(r=>setTimeout(r,0));
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const norm=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[_.\-]+/g,' ').replace(/\s+/g,' ').trim();
const safeURL=s=>{try{const u=new URL(s);return ['https:','http:'].includes(u.protocol)?u.href:'';}catch{return'';}};
const uid=()=>globalThis.crypto?.randomUUID?.()||'id-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
const bytes=n=>n>=1048576?(n/1048576).toFixed(1)+' MB':Math.round(n/1024)+' KB';
function toast(text){$('toast').textContent=text;$('toast').classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').classList.remove('show'),5000);}
function saveFile(blob,name){const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),20000);}
const jsonFile=(d,name)=>saveFile(new Blob([JSON.stringify(d,null,2)],{type:'application/json;charset=utf-8'}),name);
function b64decode(s){const raw=atob(s),out=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)out[i]=raw.charCodeAt(i);return out.buffer;}
function b64encode(buffer){const a=new Uint8Array(buffer),chunks=[];for(let i=0;i<a.length;i+=24576)chunks.push(String.fromCharCode(...a.subarray(i,i+24576)));return btoa(chunks.join(''));}
class Bus{constructor(){this.listeners=new Map();}on(k,fn){if(!this.listeners.has(k))this.listeners.set(k,new Set());this.listeners.get(k).add(fn);return()=>this.listeners.get(k)?.delete(fn);}emit(k,v){for(const fn of this.listeners.get(k)||[])fn(v);}}
const CAT={skeletal:{name:'骨骼',en:'Skeletal',color:'#b7aa88',file:'iskelet.glb',icon:'bone'},joints:{name:'关节与韧带',en:'Joints & ligaments',color:'#6faaa6',file:'eklem.glb',icon:'joint'},muscles:{name:'肌肉',en:'Muscles',color:'#bb8178',file:'kas.glb',icon:'muscle'},nerves:{name:'神经与感觉器',en:'Nerves',color:'#c1a34f',file:'sinir.glb',icon:'nerve'},organs:{name:'内脏器官',en:'Internal organs',color:'#a88498',file:'ic-organlar.glb',icon:'heart'},vessels:{name:'心血管',en:'Circulation',color:'#bd6b6d',file:'dolasim.glb',icon:'heart'},lymph:{name:'淋巴',en:'Lymphatic',color:'#94a660',file:'lenf.glb',icon:'layers'},other:{name:'本地导入',en:'Local imports',color:'#7999a0',icon:'cube'},regions:{name:'已标注面域',en:'Surface regions',color:'#77b598',icon:'brush'}};
const REGIONS={head:'头颈',spine:'脊柱',thorax:'胸腹 / 背',upper:'上肢',pelvis:'骨盆',lower:'下肢',other:'其他'};
const BASE='https://raw.githubusercontent.com/DrMuratAltun/anatomi-simulatoru/refs/heads/main/systems/';
const MIRROR='https://drmurataltun.github.io/anatomi-simulatoru/systems/';
// Model source registry (Task 11): versioned data embedded at #model-sources-data.
function loadModelSources(){
 try{const raw=document.getElementById('model-sources-data')?.textContent;if(raw&&raw.trim())return JSON.parse(raw);}catch(e){console.warn('model-sources parse failed',e);}
 return{version:1,defaultTier:'standard',sources:{standard:{bases:[BASE,MIRROR],files:{},gzip:false,available:true}}};
}
const MODEL_SOURCES=loadModelSources();
const TIER_KEY='forma-model-tier-v1';
const TIER_BASES_KEY='forma-model-bases-v1';
function readTier(){try{const t=localStorage.getItem(TIER_KEY);return MODEL_SOURCES.sources[t]?t:MODEL_SOURCES.defaultTier||'standard';}catch{return MODEL_SOURCES.defaultTier||'standard';}}
function writeTier(t){try{localStorage.setItem(TIER_KEY,t);}catch{}}
function readTierBases(){try{return JSON.parse(localStorage.getItem(TIER_BASES_KEY)||'{}');}catch{return{}}}
function writeTierBases(obj){try{localStorage.setItem(TIER_BASES_KEY,JSON.stringify(obj));}catch{}}
// Decompress gzip bytes for explicitly-served .glb.gz (local Object URL /
// octet-stream). When a server sends Content-Encoding the browser has already
// inflated, but a .gz-named file usually carries raw gzip without that header.
async function gunzip(buffer){
 if(typeof DecompressionStream==='undefined')throw Error('当前浏览器不支持 gzip 解压（DecompressionStream）');
 const stream=new Response(buffer).body.pipeThrough(new DecompressionStream('gzip'));
 return await new Response(stream).arrayBuffer();
}
const ATTRIBUTION={model:'Z-Anatomy / Gauthier Kervyn, Marcin Zielinski; derived from BodyParts3D / DBCLS.',adaptation:'DrMuratAltun/anatomi-simulatoru; upstream decimated browser GLB.',license:'Upstream distributes systems GLB as CC BY-SA 4.0; retain BodyParts3D CC BY-SA 2.1 Japan and source notices. Component-specific licences may apply.',url:'https://github.com/DrMuratAltun/anatomi-simulatoru/blob/main/ATTRIBUTION.md',source:'https://github.com/Z-Anatomy/Models-of-human-anatomy'};
const STORE_KEY='forma-study-v3';
function readStore(){try{return JSON.parse(localStorage.getItem(STORE_KEY)||'{}');}catch{return{};}}
function writeStore(data){try{localStorage.setItem(STORE_KEY,JSON.stringify(data));return true;}catch{return false;}}
class AssetCache{
 async db(){if(this.instance)return this.instance;return new Promise((res,rej)=>{if(!globalThis.indexedDB)return rej(Error('IndexedDB 不可用'));const q=indexedDB.open('forma-model-cache-v3',1);q.onupgradeneeded=()=>q.result.createObjectStore('assets',{keyPath:'sha256'});q.onsuccess=()=>{this.instance=q.result;res(q.result);};q.onerror=()=>rej(q.error);});}
 async all(){const db=await this.db();return new Promise((res,rej)=>{const q=db.transaction('assets').objectStore('assets').getAll();q.onsuccess=()=>res(q.result);q.onerror=()=>rej(q.error);});}
 async put(asset){const db=await this.db();return new Promise((res,rej)=>{const tx=db.transaction('assets','readwrite');tx.objectStore('assets').put(asset);tx.oncomplete=res;tx.onerror=()=>rej(tx.error);});}
 async clear(){const db=await this.db();return new Promise((res,rej)=>{const tx=db.transaction('assets','readwrite');tx.objectStore('assets').clear();tx.oncomplete=res;tx.onerror=()=>rej(tx.error);});}
}
class AssetManager{
 constructor(renderer,bus){this.r=renderer;this.bus=bus;this.assets=[];this.pending=new Map();this.controllers=new Set();this.cache=new AssetCache();this.cacheEnabled=true;this.cancelled=false;}
 asset(o){return this.assets.find(a=>a.id===o.assetId);}
 key(o){return (this.asset(o)?.sha256||o.assetId)+'::'+o.sourceName+'::'+(o.nodeIndex??'');}
 progress(text,pct=null){this.bus.emit('progress',{text,pct});}
 async fetch(url){const c=new AbortController();this.controllers.add(c);const timeout=setTimeout(()=>c.abort(),60000);try{const r=await fetch(url,{signal:c.signal,credentials:'omit',referrerPolicy:'no-referrer'});if(!r.ok)throw Error('HTTP '+r.status);const total=Number(r.headers.get('content-length'))||0;if(!r.body)return await r.arrayBuffer();const reader=r.body.getReader();let length=0;const chunks=[];for(;;){const{value,done}=await reader.read();if(done)break;length+=value.byteLength;if(length>750*1048576){c.abort();throw Error('单个模型超过 750 MB，请按系统拆分');}chunks.push(value);this.progress('正在载入源网格 · '+bytes(length)+(total?' / '+bytes(total):''),total?length/total*85:15);}const out=new Uint8Array(length);let off=0;for(const a of chunks){out.set(a,off);off+=a.length;}return out.buffer;}finally{clearTimeout(timeout);this.controllers.delete(c);}}
 cancel(){this.cancelled=true;for(const c of this.controllers)c.abort();this.bus.emit('loading-end');}
 async ingest(buffer,meta={},options={}){
  if(!(buffer instanceof ArrayBuffer)||buffer.byteLength>750*1048576)throw Error('无效的模型数据或文件过大');
  this.progress('校验并读取 '+(meta.filename||'源网格'),88);await tick();const hash=await sha256(buffer);
  if(meta.sha256&&meta.sha256!==hash)throw Error('模型哈希不匹配，文件可能不完整');
  const duplicate=this.assets.find(a=>a.sha256===hash);if(duplicate){this.r.catVisible[duplicate.category]=true;this.r.dirty=true;return duplicate;}
  const category=CAT[meta.category]?meta.category:'other';const id=this.assets.some(a=>a.id===meta.id)?uid():(meta.id||uid());
  const cleanMeta={id,category,filename:meta.filename||'import.glb',sourceURL:safeURL(meta.sourceURL),origin:meta.origin||'local',quality:String(meta.quality||'本地源网格').slice(0,2000),license:String(meta.license||'请核对原始素材许可').slice(0,8000),attribution:meta.attribution||null,loadedAt:meta.loadedAt||new Date().toISOString(),sha256:hash};
  const parsed=MeshEngine.MeshReader.read(buffer,cleanMeta);const asset={...cleanMeta,buffer,bytes:buffer.byteLength,objects:parsed.objects.length,triangles:parsed.objects.reduce((s,o)=>s+o.triangles,0),source:parsed.source||{},extras:parsed.extras||{},annotations:parsed.annotations||[]};
  // All positions/normals come from the supplied source. No generated anatomy.
  this.r.add(parsed.objects);this.assets.push(asset);this.r.catVisible[category]=true;this.r.catAlpha[category]??=1;
  this.r.palette.organs=[.65,.43,.49];this.r.palette.vessels=[.74,.32,.35];this.r.palette.lymph=[.58,.64,.34];this.r.palette.regions=[.42,.68,.51];
  if(options.fit!==false)this.r.fit();this.bus.emit('asset',asset);this.progress('已载入 '+asset.objects+' 个源对象',100);
  if(this.cacheEnabled&&options.cache!==false)this.cache.put(asset).catch(()=>this.bus.emit('cache-unavailable'));
  return asset;
 }
 get tier(){return readTier();}
 setTier(t){if(!MODEL_SOURCES.sources[t])throw Error('未知模型档位');writeTier(t);}
 tierSource(tier=this.tier){const src=MODEL_SOURCES.sources[tier];const custom=readTierBases()[tier];return{...src,bases:(custom&&custom.length)?custom:src.bases};}
 resolveModelURL(category,tier=this.tier){
  const src=this.tierSource(tier);const file=src.files?.[category]||CAT[category]?.file;
  if(!file)throw Error('该档位没有此系统的文件映射');
  if(!src.bases||!src.bases.length)throw Error('该档位尚未配置自托管地址（见 models/README.md）');
  return{url:src.bases[0]+file,bases:src.bases,file,gzip:!!src.gzip};
 }
 async load(category,tier=this.tier){if(this.pending.has(category))return this.pending.get(category);if(!CAT[category])throw Error('该类别没有模型源');
  const originTag='compact:'+tier;
  const found=this.assets.find(a=>a.category===category&&a.origin===originTag);if(found){this.r.catVisible[category]=true;this.r.dirty=true;this.bus.emit('asset',found);return found;}
  const src=this.tierSource(tier);
  if(!src.available&&!readTierBases()[tier]?.length)throw Error(CAT[category].name+' 的 '+src.zh+' 档位尚未生成；请使用标准档，或按 models/README.md 自托管 balanced/HD。');
  let resolved;try{resolved=this.resolveModelURL(category,tier);}catch(e){throw e;}
  this.cancelled=false;const task=(async()=>{this.bus.emit('loading-start',category);let err;
   try{
    for(const base of resolved.bases){
     if(this.cancelled)throw Error('下载已取消');
     try{
      const url=base+resolved.file;this.progress('连接 '+CAT[category].name+' 模型源 · '+(src.zh||tier),2);
      let buffer=await this.fetch(url);if(this.cancelled)throw Error('下载已取消');
      // .glb.gz delivered without Content-Encoding arrives as raw gzip; inflate locally.
      if(resolved.gzip||/\.glb\.gz$/i.test(resolved.file)){
       const dv=new DataView(buffer);
       const isGLB=dv.byteLength>4&&dv.getUint32(0,true)===0x46546C67;
       if(!isGLB){this.progress('解压 gzip 模型 · '+bytes(buffer.byteLength),86);buffer=await gunzip(buffer);}
      }
      return await this.ingest(buffer,{category,filename:resolved.file.replace(/\.gz$/,''),origin:originTag,tier,quality:(src.qualityZh||('模型档位：'+tier))+'；本应用不再减面',sourceURL:url,license:ATTRIBUTION.license,attribution:ATTRIBUTION},{fit:this.r.objects.length===0});
     }catch(e){err=e;if(this.cancelled)throw Error('下载已取消');}
    }
    throw Error('无法取得 '+CAT[category].name+' 模型。可重试、切换标准档、导入本地 GLB，或导入上一版含数据的离线 HTML。'+(err?.message?'（'+err.message+'）':''));
   }finally{this.pending.delete(category);this.bus.emit('loading-end');}})();
  this.pending.set(category,task);return task;
 }
 async importFile(file,category='other'){
  let name=file.name;
  let ext=name.split('.').pop().toLowerCase();
  if(/\.glb\.gz$/i.test(name))ext='glb.gz';
  if(file.size>1050*1048576)throw Error('文件过大，请按系统导入');
  if(['html','htm'].includes(ext)){
   // Parse inert data only. Imported HTML/JavaScript is never executed.
   const text=await file.text();const doc=new DOMParser().parseFromString(text,'text/html');const node=doc.querySelector('#payload-data');if(!node)throw Error('未发现兼容的模型数据插槽；请从旧版先导出含模型的离线 HTML');const pack=JSON.parse(node.textContent);if(!Array.isArray(pack.assets)||!pack.assets.length)throw Error('该 HTML 是无内嵌模型的启动器；请在旧版载入模型并导出离线文件');if(pack.assets.length>80)throw Error('数据包数量异常');for(const a of pack.assets){if(typeof a.data!=='string')throw Error('模型数据缺失');const{data,...meta}=a;await this.ingest(b64decode(data),meta,{fit:false});}this.r.fit();this.bus.emit('import-records',pack);return;
  }
  if(!['glb','obj','stl','glb.gz'].includes(ext))throw Error('支持 GLB / .glb.gz / OBJ / STL 或旧版离线 HTML');
  let buffer=await file.arrayBuffer();
  let importName=file.name;
  if(ext==='glb.gz'){
   const dv=new DataView(buffer);
   if(!(dv.byteLength>4&&dv.getUint32(0,true)===0x46546C67))buffer=await gunzip(buffer);
   importName=file.name.replace(/\.gz$/,'');
  }
  await this.ingest(buffer,{category,filename:importName,origin:'local',quality:'用户导入源网格；身份与单位由来源决定'});
 }
 manifest(){return{version:3,generatedAt:new Date().toISOString(),assets:this.assets.map(({buffer,...meta})=>meta),objects:this.r.objects.filter(o=>!o.transient).map(o=>({key:this.key(o),sourceName:o.sourceName,path:o.path,category:o.category,triangles:o.triangles,vertices:o.vertices}))};}
}
function rotationAround(a,b,angle){const axis=Vec.norm(Vec.sub(b,a));if(Vec.length(axis)<.5)throw Error('旋转轴两点过近');const half=angle/2;const r=M4.trs([0,0,0],[...Vec.scale(axis,Math.sin(half)),Math.cos(half)]);return M4.mul(M4.trs(a),M4.mul(r,M4.trs(Vec.scale(a,-1))));}
window.FormaCore={$ ,esc,icon,tick,clamp,norm,safeURL,uid,bytes,toast,saveFile,jsonFile,b64decode,b64encode,sha256,Bus,CAT,REGIONS,ATTRIBUTION,readStore,writeStore,AssetManager,rotationAround,MODEL_SOURCES,gunzip,readTier,writeTier,readTierBases,writeTierBases};
})();
