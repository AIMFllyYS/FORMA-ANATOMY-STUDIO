/* Curriculum runtime: versioned lesson data (assembly, motions, muscle groups).
   Data source: web/curriculum.json (embedded at #curriculum-data). All structural
   references are stable nomenclature ids; lessons never fabricate missing objects. */
(()=>{'use strict';
function load(){
 const node=document.getElementById('curriculum-data');
 if(node&&node.textContent&&node.textContent.trim()){
  try{return JSON.parse(node.textContent);}catch(e){console.warn('curriculum parse failed',e);}
 }
 return {version:1,lessons:[],orientation:{default:'unverified'}};
}
const DATA=load();
const byId=new Map((DATA.lessons||[]).map(l=>[l.id,l]));
function lesson(id){return byId.get(id)||null;}
function list(){return(DATA.lessons||[]).map(l=>({id:l.id,joint:l.joint,zh:l.zh,en:l.en,region:l.region,complete:!!l.complete}));}
function orientationCalibrated(){return DATA.orientation?.calibrated===true;}
window.FormaCurriculum={DATA,lesson,list,orientationCalibrated};
})();
