/* Safe Markdown + K-text renderer. No HTML passthrough. MIT. */
(()=>{'use strict';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const GREEK={alpha:'α',beta:'β',gamma:'γ',delta:'δ',epsilon:'ε',zeta:'ζ',eta:'η',theta:'θ',iota:'ι',kappa:'κ',lambda:'λ',mu:'μ',nu:'ν',xi:'ξ',omicron:'ο',pi:'π',rho:'ρ',sigma:'σ',tau:'τ',upsilon:'υ',phi:'φ',chi:'χ',psi:'ψ',omega:'ω',Alpha:'Α',Beta:'Β',Gamma:'Γ',Delta:'Δ',Theta:'Θ',Lambda:'Λ',Pi:'Π',Sigma:'Σ',Phi:'Φ',Omega:'Ω'};
const OPS={times:'×',div:'÷',pm:'±',mp:'∓',cdot:'·',leq:'≤',geq:'≥',neq:'≠',approx:'≈',equiv:'≡',sim:'∼',infty:'∞',partial:'∂',nabla:'∇',sum:'∑',prod:'∏',int:'∫',rightarrow:'→',leftarrow:'←',leftrightarrow:'↔',Rightarrow:'⇒',Leftarrow:'⇐',circ:'∘',degree:'°',ell:'ℓ',hbar:'ℏ',in:'∈',notin:'∉',subset:'⊂',supset:'⊃',cup:'∪',cap:'∩',emptyset:'∅',forall:'∀',exists:'∃',perp:'⊥',parallel:'∥',angle:'∠',triangle:'△',dots:'…',cdots:'⋯',ldots:'…'};
function renderMath(src,display){
 let s=String(src||'').trim();
 s=s.replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g,'($1)/($2)');
 s=s.replace(/\\sqrt\{([^{}]+)\}/g,'√($1)');
 s=s.replace(/\\(?:text|mathrm|mathbf)\{([^{}]*)\}/g,'$1');
 s=s.replace(/\\(left|right)[.([\])|]/g,'');
 s=s.replace(/\\([A-Za-z]+)\b/g,(m,n)=>GREEK[n]||OPS[n]||m);
 s=s.replace(/\^\{([^}]+)\}/g,'^$1').replace(/_\{([^}]+)\}/g,'_$1');
 s=esc(s).replace(/\^([\w.α-ωΑ-Ω]+)/g,'<sup>$1</sup>').replace(/_([\w.α-ωΑ-Ω]+)/g,'<sub>$1</sub>');
 return `<span class="md-math ktext-math${display?' is-block':''}" data-ktext="math">${s}</span>`;
}
function splitMath(text){
 const out=[];let i=0,s=String(text||'');
 while(i<s.length){
  if(s.startsWith('$$',i)){const j=s.indexOf('$$',i+2);if(j<0){out.push({t:'text',v:s.slice(i)});break;}out.push({t:'math',d:true,v:s.slice(i+2,j)});i=j+2;continue;}
  if(s[i]==='$'&&s[i+1]!=='$'){const j=s.indexOf('$',i+1);if(j>i&&!/\n/.test(s.slice(i,j))){out.push({t:'math',d:false,v:s.slice(i+1,j)});i=j+1;continue;}out.push({t:'text',v:'$'});i++;continue;}
  if(s.startsWith('\\[',i)){const j=s.indexOf('\\]',i+2);if(j<0){out.push({t:'text',v:s.slice(i)});break;}out.push({t:'math',d:true,v:s.slice(i+2,j)});i=j+2;continue;}
  if(s.startsWith('\\(',i)){const j=s.indexOf('\\)',i+2);if(j<0){out.push({t:'text',v:s.slice(i)});break;}out.push({t:'math',d:false,v:s.slice(i+2,j)});i=j+2;continue;}
  let n=i+1;while(n<s.length&&s[n]!=='$'&&!s.startsWith('\\[',n)&&!s.startsWith('\\(',n))n++;
  out.push({t:'text',v:s.slice(i,n)});i=n;
 }
 return out;
}
function safeURL(href){try{const u=new URL(href,location.href);return['https:','http:','mailto:'].includes(u.protocol)?u.href:'';}catch{return'';}}
function inline(src){
 const parts=splitMath(src);let html='';
 for(const p of parts){
  if(p.t==='math'){html+=renderMath(p.v,p.d);continue;}
  let s=esc(p.v);
  s=s.replace(/`([^`]+)`/g,(_,c)=>`<code>${c}</code>`);
  s=s.replace(/!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)/g,(_,alt,url)=>{const h=safeURL(url);return h?`<a class="md-img-link" href="${esc(h)}" target="_blank" rel="noopener noreferrer">[图：${alt||'image'}]</a>`:esc(alt);});
  s=s.replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)/g,(_,lab,url)=>{const h=safeURL(url);return h?`<a href="${esc(h)}" target="_blank" rel="noopener noreferrer">${lab}</a>`:lab;});
  s=s.replace(/==([^=]+)==/g,'<mark class="ktext-mark">$1</mark>');
  s=s.replace(/\*\*\*([^*]+)\*\*\*/g,'<strong><em>$1</em></strong>');
  s=s.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  s=s.replace(/__([^_]+)__/g,'<strong>$1</strong>');
  s=s.replace(/\*([^*\n]+)\*/g,'<em>$1</em>');
  s=s.replace(/(^|[^\w])_([^_\n]+)_([^\w]|$)/g,'$1<em>$2</em>$3');
  s=s.replace(/~~([^~]+)~~/g,'<del>$1</del>');
  s=s.replace(/\[\^([^\]]+)\]/g,'<sup class="md-fnref">$1</sup>');
  html+=s;
 }
 return html;
}
function fenceLang(info){return String(info||'').trim().split(/\s+/)[0].replace(/[^a-z0-9_+-]/gi,'').slice(0,24);}
function parseTable(rows){
 if(rows.length<2||!/^\s*\|?\s*:?-{3,}/.test(rows[1]))return null;
 const split=line=>line.replace(/^\s*\|/,'').replace(/\|\s*$/,'').split('|').map(c=>c.trim());
 const head=split(rows[0]);const body=rows.slice(2).map(split);
 let html='<div class="md-table-wrap ktext-table"><table><thead><tr>'+head.map(c=>`<th>${inline(c)}</th>`).join('')+'</tr></thead><tbody>';
 for(const r of body)html+='<tr>'+head.map((_,i)=>`<td>${inline(r[i]||'')}</td>`).join('')+'</tr>';
 return html+'</tbody></table></div>';
}
const CALLOUT={note:'提示',tip:'要点',warning:'注意',important:'重要',caution:'谨慎'};
function parseCallout(lines){
 const m=lines[0].match(/^\s*>\s*\[!(NOTE|TIP|WARNING|IMPORTANT|CAUTION)\]\s*(.*)$/i);
 if(!m)return null;
 const kind=m[1].toLowerCase();
 const rest=[m[2],...lines.slice(1).map(l=>l.replace(/^\s*>\s?/,''))];
 return `<aside class="md-callout ktext-callout is-${kind}" data-ktext="callout"><strong>${CALLOUT[kind]||kind}</strong><div>${inline(rest.join('\n'))}</div></aside>`;
}
function blocks(src){
 const lines=String(src||'').replace(/\r\n/g,'\n').split('\n');
 const out=[];let i=0;
 const flushPara=buf=>{if(buf.length){out.push(`<p>${inline(buf.join('\n')).replace(/\n/g,'<br>')}</p>`);buf.length=0;}};
 while(i<lines.length){
  const line=lines[i];
  if(!line.trim()){i++;continue;}
  if(/^```/.test(line)||/^~~~/.test(line)){
   const fence=line.slice(0,3);const info=line.slice(3);const body=[];i++;
   while(i<lines.length&&!lines[i].startsWith(fence)){body.push(lines[i]);i++;}
   if(i<lines.length)i++;
   const lang=fenceLang(info);
   out.push(`<div class="md-pre ktext-code"><header><span>${esc(lang||'text')}</span><button type="button" data-copy-code>复制</button></header><pre><code class="lang-${esc(lang||'text')}">${esc(body.join('\n'))}</code></pre></div>`);
   continue;
  }
  if(/^\s*\|.+\|/.test(line)){
   const rows=[];while(i<lines.length&&/^\s*\|/.test(lines[i])){rows.push(lines[i]);i++;}
   out.push(parseTable(rows)||`<p>${inline(rows.join('\n'))}</p>`);
   continue;
  }
  if(/^\s*>\s*\[!(NOTE|TIP|WARNING|IMPORTANT|CAUTION)\]/i.test(line)){
   const rows=[];while(i<lines.length&&/^\s*>/.test(lines[i])){rows.push(lines[i]);i++;}
   out.push(parseCallout(rows)||`<blockquote>${inline(rows.map(l=>l.replace(/^\s*>\s?/, '')).join('\n'))}</blockquote>`);
   continue;
  }
  if(/^\s*>\s?/.test(line)){
   const rows=[];while(i<lines.length&&/^\s*>/.test(lines[i])){rows.push(lines[i].replace(/^\s*>\s?/,''));i++;}
   out.push(`<blockquote>${inline(rows.join('\n')).replace(/\n/g,'<br>')}</blockquote>`);
   continue;
  }
  const hm=line.match(/^(#{1,6})\s+(.+)$/);
  if(hm){out.push(`<h${hm[1].length}>${inline(hm[2])}</h${hm[1].length}>`);i++;continue;}
  if(/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)){out.push('<hr>');i++;continue;}
  if(/^\s*[-*+]\s+/.test(line)||/^\s*\d+[.)]\s+/.test(line)){
   const ordered=/^\s*\d+[.)]\s+/.test(line);const items=[];
   while(i<lines.length&&(/^\s*[-*+]\s+/.test(lines[i])||/^\s*\d+[.)]\s+/.test(lines[i]))){
    const raw=lines[i].replace(/^\s*(?:[-*+]|\d+[.)])\s+/,'');
    const task=raw.match(/^\[([ xX])\]\s+(.*)$/);
    items.push(task?`<li class="md-task"><input type="checkbox" disabled ${task[1]!==' '?'checked':''}><span>${inline(task[2])}</span></li>`:`<li>${inline(raw)}</li>`);
    i++;
   }
   out.push(ordered?`<ol>${items.join('')}</ol>`:`<ul>${items.join('')}</ul>`);
   continue;
  }
  const para=[];
  while(i<lines.length&&lines[i].trim()&&!/^```/.test(lines[i])&&!/^#{1,6}\s/.test(lines[i])&&!/^\s*>/.test(lines[i])&&!/^\s*\|/.test(lines[i])&&!/^\s*(-{3,}|\*{3,})\s*$/.test(lines[i])&&!/^\s*[-*+]\s+/.test(lines[i])&&!/^\s*\d+[.)]\s+/.test(lines[i])){para.push(lines[i]);i++;}
  flushPara(para);
 }
 return out.join('');
}
function splitThink(raw){
 let reasoning='',content=String(raw??'');
 content=content.replace(/<think(?:ing)?>([\s\S]*?)<\/think(?:ing)?>/gi,(_,b)=>{reasoning+=(reasoning?'\n':'')+b.trim();return '';});
 const open=content.search(/<think(?:ing)?>/i);
 if(open>=0){reasoning+=(reasoning?'\n':'')+content.slice(open).replace(/<think(?:ing)?>/i,'');content=content.slice(0,open);}
 return{reasoning:reasoning.trim(),content:content.replace(/^\n+/, '')};
}
function render(src){src=String(src||'');if(src.length>120000)src=src.slice(0,120000)+'\n\n…';return blocks(src);}
function streamPlain(src){src=String(src||'');if(src.length>120000)src=src.slice(0,120000);const parts=esc(src).split(/\n{2,}/);return '<p>'+parts.join('</p><p>').replace(/\n/g,'<br>')+'</p>';}
function splitLive(src){
 const s=String(src||'');
 const lines=s.split('\n');
 let fence=null,fenceAt=-1;
 for(let i=0;i<lines.length;i++){
  const line=lines[i];
  if(fence==null&&(/^```/.test(line)||/^~~~/.test(line))){fence=line.slice(0,3);fenceAt=i;}
  else if(fence!=null&&line.startsWith(fence)){fence=null;fenceAt=-1;}
 }
 if(fence!=null&&fenceAt>=0)return{done:lines.slice(0,fenceAt).join('\n'),tail:lines.slice(fenceAt).join('\n')};
 if(!s.endsWith('\n')&&lines.length){const tail=lines.pop();return{done:lines.join('\n'),tail};}
 return{done:s,tail:''};
}
function renderTail(tail){
 if(!tail)return'';
 if(/^\s*(#{1,6}\s|```|~~~|\||>\s|[-*+]\s|\d+[.)]\s)/.test(tail))return'<div class="md-live-tail">'+streamPlain(tail)+'</div>';
 return'<p class="md-live-tail">'+inline(tail).replace(/\n/g,'<br>')+'</p>';
}
function renderLive(src){
 src=String(src||'');if(src.length>120000)src=src.slice(0,120000);
 const {done,tail}=splitLive(src);
 return(done?render(done):'')+renderTail(tail);
}
window.FormaMarkdown={render,inline,splitThink,renderMath,esc,streamPlain,renderLive,splitLive};
})();
