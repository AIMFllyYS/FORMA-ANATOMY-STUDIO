/* FormaFollow: teaching follow-strip. Guides the learner's gaze toward the
   canvas before/while the Agent acts, and offers pause / fast-forward / skip
   for animation and observation waits. Display-only control: it never
   approves a tool on its own and never mutates scene state directly. MIT. */
(()=>{'use strict';
const {$}=window.FormaCore;
const icon=n=>window.FormaCore.icon(n);
function reducedMotion(){return typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;}

// Odometer: rolling count-up used by aggregated tool chips.
function odometer(el,next){
 const prev=Number(el.dataset.count||'0');if(next===prev){return;}
 el.dataset.count=String(next);
 if(reducedMotion()){el.textContent='×'+next;return;}
 const lane=el.querySelector('.odo-lane')||(()=>{el.textContent='';const l=document.createElement('span');l.className='odo-lane';el.append(l);return l;})();
 const col=document.createElement('span');col.className='odo-col';
 col.innerHTML=`<i>${prev}</i><i>${next}</i>`;
 lane.replaceChildren(col);
 requestAnimationFrame(()=>col.classList.add('odo-go'));
}

class Follow{
 constructor(app){
  this.app=app;
  this.el=$('follow-strip');this.mirror=$('follow-mirror');
  this.waiter=null;this._doneTimer=0;
  if(this.el)this.build();
 }
 build(){
  this.el.innerHTML=`
   <span class="fs-ico" aria-hidden="true"></span>
   <span class="fs-text"><b class="fs-title"></b><small class="fs-detail"></small></span>
   <span class="fs-progress" hidden><i class="fs-track"></i><em class="fs-time" aria-hidden="true"></em></span>
   <span class="fs-actions">
    <button type="button" class="fs-btn" data-fs="pause" hidden aria-label="暂停"><span class="fs-pause-ico">${icon('pause')}</span><span class="fs-play-ico" hidden>${icon('play')}</span></button>
    <button type="button" class="fs-btn fs-rate" data-fs="rate" hidden aria-label="切换播放速度"><b>1×</b></button>
    <button type="button" class="fs-btn" data-fs="skip" hidden aria-label="跳过当前动画 / 停留">${icon('skip')}</button>
    <button type="button" class="fs-btn fs-deny" data-fs="deny" hidden>${icon('close')}<span>拒绝</span></button>
    <button type="button" class="fs-btn fs-approve" data-fs="approve" hidden>${icon('check')}<span>允许一次</span></button>
   </span>`;
  this.$=s=>this.el.querySelector(s);
  this.el.addEventListener('click',e=>{
   const b=e.target.closest('[data-fs]');if(!b)return;
   const k=b.dataset.fs;
   if(k==='pause')this.togglePause();
   else if(k==='rate')this.cycleRate();
   else if(k==='skip')this.waiter?.skip();
   else if(k==='approve')this._decide?.(true);
   else if(k==='deny')this._decide?.(false);
  });
 }
 _render({phase,ico,title,detail=''}={}){
  if(!this.el)return;
  this.el.hidden=false;this.el.dataset.phase=phase;
  this.$('.fs-ico').innerHTML=ico?icon(ico):'';
  this.$('.fs-title').textContent=title||'';
  const d=this.$('.fs-detail');d.textContent=detail||'';d.style.display=detail?'':'none';
  this.mirror&&(this.mirror.hidden=!title,this.mirror.textContent=title||'');
 }
 _actions(names){
  for(const b of this.el.querySelectorAll('.fs-btn'))b.hidden=!names.includes(b.dataset.fs);
 }
 _progress(on){this.$('.fs-progress').hidden=!on;}
 // Phase: split-second preview right before an instant canvas mutation.
 announce(meta,detail){this._clearDone();this._render({phase:'announce',ico:meta?.ico||'cube',title:'即将'+(meta?.zh||'操作画布'),detail:detail?('请看画布 · '+detail):'请看画布中央'});this._actions([]);}
 // Split-second gaze cue before an instant canvas mutation. Skippable;
 // collapses to nothing under prefers-reduced-motion.
 lead(ms,meta,detail,signal){
  this._clearDone();
  if(reducedMotion())return Promise.resolve('done');
  if(this.waiter)this.waiter.cancel();
  const w=new Waiter({ms,kind:'hold',signal,finish:()=>{if(this.waiter===w)this.waiter=null;}});
  this.waiter=w;
  this._render({phase:'announce',ico:meta?.ico||'cube',
   title:'即将'+(meta?.zh||'操作画布'),detail:detail||'请看画布中央'});
  this._actions(['skip']);this._progress(false);
  return w.promise;
 }
 // Phase: instant (synchronous) canvas tools.
 running(meta,detail){this._clearDone();this._render({phase:'running',ico:meta?.ico||'cube',title:(meta?.zh||'操作')+'中',detail});this._actions([]);this._progress(false);}
 // Phase: tool authorization. Buttons resolve the SAME promise as the card.
 asking(meta,detail,decide){
  this._clearDone();
  this._decide=(ok)=>{this._decide=null;decide?.(ok);};
  this._render({phase:'asking',ico:meta?.ico||'cube',title:'请求'+(meta?.zh||'操作画布'),detail});
  this._actions(['deny','approve']);this._progress(false);
 }
 endAsking(){this._decide=null;}
 // Phase: timed animation (timeline) or post-tool observation hold.
 // Returns a promise resolved on natural finish / skip / abort.
 wait(ms,{kind='hold',ico,title,detail='',timeline=null,signal=null}={}){
  this._clearDone();
  if(this.waiter)this.waiter.cancel();
  const w=new Waiter({ms,kind,timeline,signal,
   tick:(frac,remain,rateLabel,paused)=>this._tick(frac,remain,rateLabel,paused),
   finish:()=>{if(this.waiter===w){this.waiter=null;this._progress(false);}}});
  this.waiter=w;
  const isAnim=kind==='anim';
  this._render({phase:isAnim?'playing':'holding',ico:ico||(isAnim?'rotate':'focus'),
   title:title||(isAnim?'动画播放中':'观察中 · 请看画布'),detail});
  const controls=reducedMotion()?['skip']:(isAnim?['pause','rate','skip']:['pause','skip']);
  this._actions(controls);this._progress(true);
  this._tick(0,ms,w.rate,false);
  return w.promise;
 }
 _tick(frac,remain,rate,paused){
  if(!this.el)return;
  const tr=this.$('.fs-track');tr.style.transform=`scaleX(${Math.max(0,Math.min(1,frac))})`;
  const s=Math.max(0,Math.ceil(remain/1000));
  this.$('.fs-time').textContent=s+'s';
  const rateBtn=this.$('[data-fs=rate] b');if(rateBtn)rateBtn.textContent=rate+'×';
  this.$('.fs-pause-ico').hidden=paused;this.$('.fs-play-ico').hidden=!paused;
  this.$('[data-fs=pause]').setAttribute('aria-label',paused?'继续':'暂停');
 }
 togglePause(){const w=this.waiter;if(!w)return;w.paused?w.resume():w.pause();}
 cycleRate(){this.waiter?.cycleRate();}
 // Phase: transient result, auto-dismiss.
 done(meta,{denied=false,error=false,cancelled=false,detail=''}={}){
  this._clearDone();this.waiter=null;this._progress(false);this._actions([]);
  const phase=denied?'denied':error?'error':cancelled?'cancelled':'done';
  const title=denied?'已拒绝':error?'执行失败':cancelled?'已取消':(meta?meta.zh+'完成':'已完成');
  this._render({phase,ico:denied?'close':error?'close':meta?.ico||'check',title,detail});
  this._doneTimer=setTimeout(()=>this.hide(),denied||error?1800:1100);
 }
 _clearDone(){if(this._doneTimer){clearTimeout(this._doneTimer);this._doneTimer=0;}}
 hide(){
  this._clearDone();
  if(this.waiter){this.waiter.cancel();this.waiter=null;}
  this._decide=null;
  if(this.el){this.el.hidden=true;this.el.dataset.phase='';this._progress(false);this._actions([]);}
  if(this.mirror)this.mirror.hidden=true;
 }
}

// Interruptible, pause/rate/skip-aware wait. Anim waiter observes the
// timeline's public playing flag via rAF; hold waiter runs a virtual clock.
class Waiter{
 constructor({ms,kind,timeline,signal,tick,finish}){
  this.ms=Math.max(0,ms|0);this.kind=kind;this.timeline=timeline||null;this.signal=signal;
  this.tick=tick;this.finish=finish;this.rate=1;this.paused=false;this._done=false;this._reason='done';
  this._elapsed=0;this._last=performance.now();this._raf=0;
  this.promise=new Promise(res=>{this._resolve=res;});
  this._onAbort=()=>{this._reason='cancel';this._end(false);}
  if(signal){if(signal.aborted){queueMicrotask(()=>this._end(false));}else signal.addEventListener('abort',this._onAbort,{once:true});}
  this._loop=this._loop.bind(this);this._raf=requestAnimationFrame(this._loop);
 }
 _loop(now){
  if(this._done)return;
  this._raf=requestAnimationFrame(this._loop);
  const dt=now-this._last;this._last=now;
  if(this.kind==='anim'){
   const tl=this.timeline;
   // Mirror the timeline's transport controls; progress uses an independent
   // virtual clock so looped joint motions (elapsed resets each loop) still
   // report a monotone overall fraction.
   if(!this.paused&&tl&&!tl.playing&&tl.paused)this.paused=true;
   else if(this.paused&&tl&&tl.playing)this.paused=false;
   if(!this.paused&&tl&&!tl.playing){this._end(true);return;}
   this._elapsed=Math.min(this.ms,this._elapsed+(this.paused?0:dt*this.rate));
  }else{
   if(!this.paused)this._elapsed+=dt*this.rate;
  }
  if(this._elapsed>=this.ms){this._end(true);return;}
  this.tick?.(this._elapsed/this.ms,this.ms-this._elapsed,this.rate,this.paused);
 }
 pause(){
  if(this._done||this.paused)return;this.paused=true;
  if(this.kind==='anim'&&this.timeline?.playing)this.timeline.pause();
 }
 resume(){
  if(this._done||!this.paused)return;this.paused=false;
  if(this.kind==='anim'&&this.timeline)this.timeline.resume();
 }
 cycleRate(){
  if(this._done)return;
  this.rate=this.rate===1?2:this.rate===2?4:1;
  if(this.kind==='anim'&&this.timeline?.playing&&!this.paused)this.timeline.setRate(this.rate);
 }
 skip(){if(!this._done){this._reason='skip';if(this.kind==='anim'&&this.timeline)this.timeline.finishNow();this._elapsed=this.ms;this._end(true);}}
 // Abort/stop path: do not force terminal state, just release the await.
 cancel(){this._reason='cancel';this._end(false);}
 _end(natural){
  if(this._done)return;this._done=true;
  cancelAnimationFrame(this._raf);
  this.signal?.removeEventListener?.('abort',this._onAbort);
  this.finish?.(natural);this._resolve(this._reason);
 }
}
window.FormaFollow={Follow,Waiter,odometer};
})();
