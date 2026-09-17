/* Deterministic timeline player for teaching animations.
   Channels: per-object assembly offset, rigid motion matrix, camera, highlight
   state. Display-only transforms — source vertices are never mutated.
   rAF clock; a new canvas write op / stop / scene switch cancels playback.
   prefers-reduced-motion (or instant:true) jumps straight to the final state.
   Total scheduled time is clamped to the user's animationBudgetSeconds. */
(()=>{'use strict';
const E=window.MeshEngine,C=window.FormaCore;
const EASINGS={
 linear:t=>t,
 easeOutCubic:t=>1-Math.pow(1-t,3),
 easeInOutCubic:t=>t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2,
 easeInOutQuad:t=>t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2
};
const lerp=(a,b,t)=>a+(b-a)*t;
const vlerp=(a,b,t)=>a.map((v,i)=>lerp(v,b[i],t));
function angLerp(a,b,t){return a+((((b-a+540)%360)+360)%360-180)*t;}
function reduced(){return typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;}
// Overlapping segments: each has delay/duration and applies its own channels.
// Sticky segments (isState) keep their terminal value for the rest of playback.
class Timeline{
 constructor(r){this.r=r;this.playing=false;this.paused=false;this.raf=0;this.startAt=0;this.elapsed=0;this.total=0;this.segments=[];this.onfinish=null;this.oncancel=null;this.loop=1;this.loopPlayed=0;this.rate=1;this._lastNow=0;this._boundFrame=this._frame.bind(this);}
 play(segments,{onfinish,oncancel,budgetSeconds=60,instant=false,loop=1}={}){
  this._cancelInternal();
  this.segments=(segments||[]).filter(Boolean);
  if(!this.segments.length)return;
  this.onfinish=onfinish||null;this.oncancel=oncancel||null;this.loop=Math.max(1,loop|0);this.loopPlayed=0;
  this.total=this.segments.reduce((s,x)=>s+(x.delay||0)+(x.duration||0),0);
  if(budgetSeconds>0&&this.total>budgetSeconds){
   const k=budgetSeconds/this.total;
   this.segments=this.segments.map(x=>({...x,delay:(x.delay||0)*k,duration:(x.duration||0)*k}));
   this.total=budgetSeconds;
  }
  if(reduced()||instant){this.renderAt(this.total);this._finish();return;}
  this.playing=true;this.paused=false;this.elapsed=0;this.rate=1;this._lastNow=performance.now();
  this.raf=requestAnimationFrame(this._boundFrame);
 }
 // Virtual clock: elapsed accumulates wall-clock deltas scaled by rate, so
 // playback speed changes never alter per-frame renderAt(t) determinism.
 _frame(now){
  if(!this.playing||this.paused){this._lastNow=now;return;}
  const dt=Math.max(0,(now-this._lastNow)/1000);this._lastNow=now;
  this.elapsed+=dt*this.rate;
  this.renderAt(this.elapsed);
  if(this.elapsed>=this.total){
   if(++this.loopPlayed<this.loop){this.elapsed=0;this.renderAt(0);this.raf=requestAnimationFrame(this._boundFrame);return;}
   this.renderAt(this.total);this._finish();return;
  }
  this.raf=requestAnimationFrame(this._boundFrame);
 }
 // Fast-forward cycles 1x -> 2x -> 4x; virtual clock keeps final state exact.
 setRate(rate){const r=Number(rate);if(r===1||r===2||r===4)this.rate=r;return this.rate;}
 cycleRate(){return this.setRate(this.rate===1?2:this.rate===2?4:1);}
 // Skip to the end: render the exact terminal state, then finish normally.
 finishNow(){if(!this.playing){return;}this.renderAt(this.total);this._finish();}
 pause(){if(!this.playing||this.paused)return;this.paused=true;cancelAnimationFrame(this.raf);}
 resume(){if(!this.paused)return;this.paused=false;this._lastNow=performance.now();this.raf=requestAnimationFrame(this._boundFrame);}
 renderAt(t){
  const r=this.r;
  // Reset display channels each frame; sticky state segments re-apply below.
  r.timelineOffsets.clear();
  r.highlightState.clear();
  r.timelineMatrixFor=()=>null;
  let cursor=0;
  for(const s of this.segments){
   const start=cursor+(s.delay||0),dur=Math.max(1e-4,s.duration||0),end=start+dur;cursor=end;
   if(t>=start&&t<=end){
    const local=s.duration?Math.max(0,Math.min(1,(t-start)/dur)):1;
    const k=s.easing?(EASINGS[s.easing]||EASINGS.linear)(local):local;
    s.apply?.(k,{ended:false});
   }else if(t>end&&s.sticky){
    // Sticky segments (assembly rest position, persistent highlight) hold
    // their terminal value; non-sticky rigid motions return to neutral.
    s.apply?.(1,{ended:true});
   }
  }
  r.dirty=true;
 }
 _finish(){this.playing=false;this.paused=false;cancelAnimationFrame(this.raf);const fn=this.onfinish;this.onfinish=this.oncancel=null;fn&&fn();}
 _cancelInternal(){this.playing=false;this.paused=false;cancelAnimationFrame(this.raf);this.r.timelineOffsets.clear();this.r.highlightState.clear();this.r.timelineMatrixFor=()=>null;this.segments=[];}
 // User / external stop: channels cleared and cancel callback fired.
 stop(){const was=this.playing||this.segments.length>0;const fn=this.oncancel;this._finishReset();if(was)fn&&fn();}
 _finishReset(){this.playing=false;this.segments=[];this.r.timelineOffsets.clear();this.r.highlightState.clear();this.r.timelineMatrixFor=()=>null;this.r.dirty=true;}
}
// ---- segment builders -----------------------------------------------------
function cameraMove(r,to,{delay=0,duration=1,easing='easeInOutCubic'}={}){
 const from={target:[...r.target],yaw:r.yaw,pitch:r.pitch,span:r.span};
 return{delay,duration,easing,apply(k){
  if(to.target)r.target=vlerp(from.target,to.target,k);
  if(Number.isFinite(to.yaw))r.yaw=angLerp(from.yaw,to.yaw,k);
  if(Number.isFinite(to.pitch))r.pitch=lerp(from.pitch,to.pitch,k);
  if(Number.isFinite(to.span))r.span=lerp(from.span,to.span,k);
 }};
}
// Objects travel from an exploded outward offset back to assembly position.
// factor<0 reverses into disassembly. Source vertices never move (offset only).
function assembly(r,objects,{from=.6,to=0,delay=0,duration=1.2,easing='easeOutCubic'}={}){
 const center=r.explodeCenter||(()=>{const b=E.boundsEmpty();for(const o of objects){E.boundsAdd(b,o.bounds.min);E.boundsAdd(b,o.bounds.max);}return E.boundsCenter(b);})();
 const items=objects.map(o=>({id:o.id,dir:E.Vec.sub(o.center,center)}));
 return{sticky:true,delay,duration,easing,apply(k){
  const f=lerp(from,to,k);
  for(const{id,dir}of items)r.timelineOffsets.set(id,E.Vec.scale(dir,f));
 }};
}
// One-way rigid rotation over [startAngle,endAngle]. Non-sticky: returns to
// neutral after the segment unless chained with another motion segment.
function rigidMotion(r,{ids,pointA,pointB,startAngle=0,endAngle=30,delay=0,duration=2,easing='easeInOutCubic'}={}){
 return{delay,duration,easing,apply(k){
  const ang=lerp(startAngle,endAngle,k);
  const m=C.rotationAround(pointA,pointB,ang*Math.PI/180);
  r.timelineMatrixFor=o=>ids.has(o.id)?m:null;
 }};
}
// Teaching rep: oscillates -amplitude .. +amplitude and returns to neutral.
// Explicitly a rigid approximation, never a physiological range claim.
function rigidSweep(r,{ids,pointA,pointB,amplitude=30,delay=0,duration=3,easing='easeInOutQuad'}={}){
 return{delay,duration,easing:'linear',apply(k){
  const phase=Math.sin(k*Math.PI); // 0..1..0
  const eased=(EASINGS[easing]||EASINGS.linear)(phase);
  const ang=(-amplitude)+2*amplitude*eased;
  const m=C.rotationAround(pointA,pointB,ang*Math.PI/180);
  r.timelineMatrixFor=o=>ids.has(o.id)?m:null;
 }};
}
// Highlight state is sticky from activation until the timeline ends / is stopped.
function highlight(r,entries,{delay=0,duration=0.001,easing='linear'}={}){
 return{sticky:true,delay,duration,easing,apply(){for(const[id,state]of entries)r.highlightState.set(id,state);}};
}
window.FormaTimeline={Timeline,cameraMove,assembly,rigidMotion,rigidSweep,highlight,EASINGS,lerp,vlerp};
})();
