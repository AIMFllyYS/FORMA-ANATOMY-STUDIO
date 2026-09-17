/* Nomenclature runtime: canonical zh/en/la identity + functional taxonomy.
   Single data source is web/nomenclature.json (built by tools/build_nomenclature.py).
   Knowledge cards remain a separate study layer; this module never fabricates a
   name for an unmatched node — the source name stays visible with an "unmapped" mark. */
(()=>{'use strict';
const {norm}=FormaCore;

function loadData(){
 const node=document.getElementById('nomenclature-data');
 if(node&&node.textContent&&node.textContent.trim()){
  try{return JSON.parse(node.textContent);}catch(e){console.warn('nomenclature data parse failed',e);}
 }
 return null;
}
const DATA=loadData();
const records=DATA?.records||{};
// Primary index: system -> nodeIndex -> assignment
const byNode={};
// Fallback for imported GLBs whose node indices differ: system -> norm(base)+side -> assignment.
// byNameBase additionally maps the side-less base name to the first assignment
// so unsided runtime objects (or imported GLBs without side suffix) still match.
const byName={},byNameBase={};
for(const a of DATA?.assignments||[]){
 if(!a)continue;
 (byNode[a.system]??=Object.create(null))[a.nodeIndex]=a;
 const base=norm(String(a.name||'').replace(/[._-]?\b(l|r|left|right)\b\s*$/i,'').replace(/\s+/g,' ').trim());
 const k=base+'|'+(a.side||'');
 (byName[a.system]??=Object.create(null))[k]??=a;
 ((byNameBase[a.system]??=Object.create(null))[base]??=a);
}
function trustLabel(status){return status==='reviewed'?'已审校':status==='pending'?'待审':'未映射';}
function baseName(raw){
 return norm(String(raw||'').replace(/[._-]?\b(l|r|left|right)\b\s*$/i,'').replace(/\s+/g,' ').trim());
}
function resolve(o){
 if(!o||o.transient)return null;
 if(o._nomenclature!==undefined)return o._nomenclature;
 const sys=o.category;
 let a=null;
 const nodeHit=byNode[sys]&&Number.isInteger(o.nodeIndex)?byNode[sys][o.nodeIndex]:null;
 // nodeIndex is only trusted when the node base name agrees, guarding against
 // index collisions across different GLB versions / synthetic test meshes.
 if(nodeHit&&baseName(o.sourceName||o.name)===baseName(nodeHit.name))a=nodeHit;
 if(!a&&byName[sys]){
  const n=baseName(o.sourceName||o.name);
  const sd=FormaKnowledge?.side?FormaKnowledge.side(o):'';
  a=byName[sys][n+'|'+sd]||byName[sys][n+'|']||byNameBase[sys]?.[n]||null;
 }
 let rec=null;
 if(a?.id)rec=records[a.id]||null;
 // An assignment without zh still means "no canonical name" — keep source visible.
 const out=(rec&&(rec.zh||rec.la))?{rec,assignment:a,status:a?.status||rec.status||'unmatched'}:null;
 o._nomenclature=out;
 return out;
}
function reset(o){if(o)delete o._nomenclature;}
// Taxonomy used by the structure tree: region -> group -> subgroup.
// Returns null when the nomenclature layer has no group for this object,
// so callers can fall back to the legacy card-based family grouping.
function taxonomy(o){
 const x=resolve(o);
 if(!x?.rec?.group)return null;
 const r=x.rec;
 return{region:r.region||'other',group:r.group,subgroup:r.subgroup||'',status:x.status};
}
function identity(o){
 const x=resolve(o);
 return x?{id:x.rec.id,zh:x.rec.zh||'',en:x.rec.en||'',la:x.rec.la||'',
  side:x.assignment?.side||'',group:x.rec.group||'',subgroup:x.rec.subgroup||'',
  region:x.rec.region||'',method:x.rec.method||'',status:x.status,
  sources:x.rec.sources||{}}:null;
}
window.FormaNomenclature={DATA,records,resolve,identity,taxonomy,reset,trustLabel,
 get loaded(){return !!DATA;}};
})();
