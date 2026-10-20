/* Local, source-linked study knowledge; not a mesh generator. */
(()=>{'use strict';
const {norm,CAT,REGIONS}=FormaCore;
const LEGACY_TERMS=[['superior vertebral notch','上椎切迹'],['inferior vertebral notch','下椎切迹'],['superior articular process','上关节突'],['inferior articular process','下关节突'],['superior articular facet','上关节面'],['inferior articular facet','下关节面'],['transverse process','横突'],['spinous process','棘突'],['mammillary process','乳突'],['mamillary process','乳突'],['accessory process','副突'],['pars interarticularis','关节突间部'],['vertebral foramen','椎孔'],['intervertebral foramen','椎间孔'],['vertebral body','椎体'],['body of vertebra','椎体'],['vertebral arch','椎弓'],['lumbar vertebrae','腰椎'],['lumbar vertebra','腰椎'],['lumbar','腰部'],['thoracic vertebra','胸椎'],['cervical vertebra','颈椎'],['intervertebral disc','椎间盘'],['intervertebral disk','椎间盘'],['ligamentum flavum','黄韧带'],['ligamenta flava','黄韧带'],['anterior longitudinal ligament','前纵韧带'],['posterior longitudinal ligament','后纵韧带'],['interspinous ligament','棘间韧带'],['supraspinous ligament','棘上韧带'],['intertransverse ligament','横突间韧带'],['articular cartilage','关节软骨'],['joint capsule','关节囊'],['spinal cord','脊髓'],['cauda equina','马尾'],['spinal nerve','脊神经'],['dorsal root ganglion','脊神经节'],['dorsal root','后根'],['ventral root','前根'],['dura mater','硬脊膜/硬脑膜'],['sciatic nerve','坐骨神经'],['femoral nerve','股神经'],['tibial nerve','胫神经'],['common fibular nerve','腓总神经'],['common peroneal nerve','腓总神经'],['median nerve','正中神经'],['radial nerve','桡神经'],['ulnar nerve','尺神经'],['brachial plexus','臂丛'],['lumbar plexus','腰丛'],['sacral plexus','骶丛'],['clavicle','锁骨'],['scapula','肩胛骨'],['humerus','肱骨'],['radius','桡骨'],['ulna','尺骨'],['femur','股骨'],['patella','髌骨'],['tibia','胫骨'],['fibula','腓骨'],['sacrum','骶骨'],['coccyx','尾骨'],['hip bone','髋骨'],['coxal bone','髋骨'],['ilium','髂骨'],['ischium','坐骨'],['pubis','耻骨'],['sternum','胸骨'],['rib','肋骨'],['mandible','下颌骨'],['maxilla','上颌骨'],['frontal bone','额骨'],['parietal bone','顶骨'],['temporal bone','颞骨'],['occipital bone','枕骨'],['sphenoid','蝶骨'],['ethmoid','筛骨'],['zygomatic','颧骨'],['nasal bone','鼻骨'],['hyoid','舌骨'],['atlas','寰椎'],['axis','枢椎'],['talus','距骨'],['calcaneus','跟骨'],['navicular','足舟骨'],['cuboid','骰骨'],['cuneiform','楔骨'],['scaphoid','手舟骨'],['lunate','月骨'],['triquetrum','三角骨'],['pisiform','豌豆骨'],['trapezium','大多角骨'],['trapezoid','小多角骨'],['capitate','头状骨'],['hamate','钩骨'],['metacarpal','掌骨'],['metatarsal','跖骨'],['proximal phalanx','近节指/趾骨'],['middle phalanx','中节指/趾骨'],['distal phalanx','远节指/趾骨'],['deltoid','三角肌'],['supraspinatus','冈上肌'],['infraspinatus','冈下肌'],['teres minor','小圆肌'],['teres major','大圆肌'],['subscapularis','肩胛下肌'],['biceps brachii','肱二头肌'],['triceps brachii','肱三头肌'],['brachialis','肱肌'],['brachioradialis','肱桡肌'],['pectoralis major','胸大肌'],['pectoralis minor','胸小肌'],['trapezius','斜方肌'],['latissimus dorsi','背阔肌'],['serratus anterior','前锯肌'],['rhomboid major','大菱形肌'],['rhomboid minor','小菱形肌'],['levator scapulae','肩胛提肌'],['sternocleidomastoid','胸锁乳突肌'],['erector spinae','竖脊肌'],['multifidus','多裂肌'],['rotatores','回旋肌'],['quadratus lumborum','腰方肌'],['psoas major','腰大肌'],['psoas minor','腰小肌'],['iliacus','髂肌'],['iliopsoas','髂腰肌'],['rectus abdominis','腹直肌'],['external oblique','腹外斜肌'],['internal oblique','腹内斜肌'],['transversus abdominis','腹横肌'],['gluteus maximus','臀大肌'],['gluteus medius','臀中肌'],['gluteus minimus','臀小肌'],['piriformis','梨状肌'],['obturator internus','闭孔内肌'],['obturator externus','闭孔外肌'],['quadratus femoris','股方肌'],['rectus femoris','股直肌'],['vastus lateralis','股外侧肌'],['vastus medialis','股内侧肌'],['vastus intermedius','股中间肌'],['biceps femoris','股二头肌'],['semitendinosus','半腱肌'],['semimembranosus','半膜肌'],['sartorius','缝匠肌'],['gracilis','股薄肌'],['adductor magnus','大收肌'],['adductor longus','长收肌'],['adductor brevis','短收肌'],['pectineus','耻骨肌'],['tensor fasciae latae','阔筋膜张肌'],['gastrocnemius','腓肠肌'],['soleus','比目鱼肌'],['plantaris','跖肌'],['popliteus','腘肌'],['tibialis anterior','胫骨前肌'],['tibialis posterior','胫骨后肌'],['fibularis longus','腓骨长肌'],['fibularis brevis','腓骨短肌'],['extensor digitorum longus','趾长伸肌'],['flexor digitorum longus','趾长屈肌'],['flexor hallucis longus','拇趾长屈肌'],['extensor hallucis longus','拇趾长伸肌'],['anterior cruciate ligament','前交叉韧带'],['posterior cruciate ligament','后交叉韧带'],['medial meniscus','内侧半月板'],['lateral meniscus','外侧半月板'],['acetabular labrum','髋臼唇'],['glenoid labrum','关节盂唇'],['calcaneal tendon','跟腱'],['achilles tendon','跟腱'],['pedicle','椎弓根'],['lamina','椎弓板'],['endplate','终板'],['end plate','终板']].sort((a,b)=>b[0].length-a[0].length);
const data=JSON.parse(document.getElementById('knowledge-data').textContent);
const cards=data.cards;const byId=new Map(cards.map(c=>[c.id,c]));
const cleanName=s=>norm(s).replace(/\b(left|right|sinister|dexter)\b/g,'').replace(/\([^)]*\)/g,' ').replace(/\b[lr]\b$/,'').replace(/\b0{2,}\d+$/,'').replace(/\s+/g,' ').trim();
const exact=new Map(cards.map(c=>[cleanName(c.en),c]));
const extras={atlas:'C1',axis:'C2','hip bone':'hip','coxal bone':'hip','os coxae':'hip','os sacrum':'sacrum',kneecap:'patella','calcaneum':'calcaneus'};
const wordToN={first:1,second:2,third:3,fourth:4,fifth:5,sixth:6,seventh:7,eighth:8,ninth:9,tenth:10,eleventh:11,twelfth:12};
function side(o){const raw=String(o.sourceName||o.name||'');const n=norm(raw);if(/\b(left|sinister)\b|[._ -]l(?:\b|$)/i.test(raw)||/^左/.test(raw))return'L';if(/\b(right|dexter)\b|[._ -]r(?:\b|$)/i.test(raw)||/^右/.test(raw))return'R';return'';}
function numericalName(n){let m=n.match(/\b([ctl])\s*([1-9]|1[0-2])\b/);if(m&&/vertebr|^[ctl]\s*\d|spine|椎/.test(n))return byId.get(m[1].toUpperCase()+m[2]);if(/vertebr/.test(n)){const type=/lumbar/.test(n)?'L':/thoracic/.test(n)?'T':/cervical/.test(n)?'C':null;if(type){const num=n.match(/\b(1[0-2]|[1-9])(?:st|nd|rd|th)?\b/);const val=num?.[1]||Object.entries(wordToN).find(([w])=>n.includes(w))?.[1];if(val)return byId.get(type+val);}}
 if(/\brib\b/.test(n)&&!/cartilage/.test(n)){const num=n.match(/\b(1[0-2]|[1-9])(?:st|nd|rd|th)?\b/);const val=num?.[1]||Object.entries(wordToN).find(([w])=>n.includes(w))?.[1];if(val)return byId.get('rib'+val);}return null;}
function cardFor(o){if(o._knowledge!==undefined)return o._knowledge;let name=cleanName(o.sourceName||o.name),c=byId.get(o.extras?.canonicalId)||exact.get(name)||numericalName(name);if(!c&&extras[name])c=byId.get(extras[name]);let exactMatch=!!c;if(c&&!o.extras?.canonicalId&&/\b(head of|body of|process of|facet of|foramen of|notch of|neck of|surface of|border of|angle of)\b/.test(name))exactMatch=false;
 if(!c){const same=cards.filter(c=>c.cat===o.category||o.category==='other'||o.category==='organs'&&c.id==='heart'||o.category==='vessels'&&c.id==='heart');const scored=same.map(c=>{const en=cleanName(c.en),aliases=[en,...Object.keys(extras).filter(k=>extras[k]===c.id)];const score=Math.max(0,...aliases.map(a=>new RegExp('(?:^|\\s)'+a.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?:$|\\s)').test(name)?a.length:0));return{c,score};}).filter(x=>x.score>0).sort((a,b)=>b.score-a.score);c=scored[0]?.c;}
 o._knowledgeMatch=c?(exactMatch?'exact':'related'):'none';o._knowledge=c||null;return o._knowledge;
}
function prettyEn(s){s=String(s||'').trim();return s?s.charAt(0).toUpperCase()+s.slice(1):'';}
function pinyin(text){
 const data=window.FormaPinyin||{},phrase=data.phrase||{},chars=data.char||{};
 text=String(text||'');if(!text)return '';if(phrase[text])return phrase[text];
 return text.replace(/[\u4e00-\u9fff]+/g,chunk=>{
  if(phrase[chunk])return phrase[chunk];
  const out=[];let i=0;
  while(i<chunk.length){
   let hit=null,len=0;
   for(let n=Math.min(8,chunk.length-i);n>=2;n--){const s=chunk.slice(i,i+n);if(phrase[s]){hit=phrase[s];len=n;break;}}
   if(hit){out.push(hit);i+=len;}else{out.push(chars[chunk[i]]||chunk[i]);i++;}
  }
  return out.join(' ');
 }).replace(/\s*([/·])\s*/g,' $1 ').replace(/([\u00C0-\u024Fa-z])(\d)/g,'$1 $2').replace(/(\d)(?=[\u00C0-\u024Fa-z])/g,'$1 ').replace(/\s+/g,' ').trim();
}
function foldPy(s){return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();}
const NOM=window.FormaNomenclature;
function nomId(o){return NOM?.identity(o)?.id||null;}
function nomStatus(o){return NOM?.identity(o)?.status||'unmatched';}
function names(o){
 if(!o)return{zh:'',en:'',la:'',py:'',matched:false,status:'unmatched'};
 if(o.transient){const zh=o.name||'';return{zh,en:o.sourceName||zh,la:'',py:pinyin(zh),matched:false,status:'unmatched'};}
 const c=cardFor(o),raw=String(o.sourceName||o.name||''),n=cleanName(raw);
 const ident=NOM?NOM.identity(o):null;
 let zh=ident?.zh||(o._knowledgeMatch==='exact'?c?.zh:null);
 let en=ident?.en||(o._knowledgeMatch==='exact'?c?.en:null);
 const la=ident?.la||'';
 if(!zh){const legacy=LEGACY_TERMS.find(([e])=>cleanName(e)===n);if(legacy){zh=legacy[1];if(!en)en=legacy[0];}}
 const sd=ident?.side||side(o),enSide=sd==='L'?'Left ':sd==='R'?'Right ':'';
 // 教材语序是「右肺尖段动脉」，不是「右侧 · 肺尖段动脉」。名称本身已含左/右时不再叠加。
 const withSide=label=>!label||!sd||/^[左右]/.test(label)?label:(sd==='L'?'左':'右')+label;
 if(zh){const full=withSide(zh);const baseEn=prettyEn(en||'');const showEn=/\b(left|right)\b/i.test(baseEn)?baseEn:prettyEn((enSide+baseEn).trim());return{zh:full,en:showEn,la,py:pinyin(full),matched:true,status:ident?.status||'pending',id:ident?.id||null,group:ident?.group||'',subgroup:ident?.subgroup||''};}
 return{zh:raw,en:prettyEn(raw),la:'',py:'',matched:false,status:'unmatched',id:null,group:'',subgroup:''};
}
function title(o){return names(o).zh;}
function englishName(o){return names(o).en;}
function region(o){const t=NOM?.taxonomy(o);if(t?.region&&REGIONS[t.region])return t.region;const c=cardFor(o);if(c){if(/^[CTL]\d+$/.test(c.id)||['sacrum','coccyx'].includes(c.id))return'spine';if(c.region==='trunk')return'thorax';if(c.region==='neck')return'head';if(c.region==='back')return'thorax';return REGIONS[c.region]?c.region:'other';}const n=norm([o.name,...o.path||[],...o.collectionPaths||[]].join(' '));for(const[k,re]of [['spine',/vertebr|spinal|sacrum|coccyx/],['upper',/humer|radial|ulnar|forearm|hand|carpal|clavicl|scapul|shoulder|brachii/],['lower',/femur|femor|tibial|fibul|patell|foot|tarsal|talus|calcane|thigh|leg/],['pelvis',/pelvi|hip bone|coxal|iliac|ilium|ischi|pubi/],['head',/skull|cranial|brain|cerebr|face|frontal|parietal|occipital|temporal|sphenoid|maxilla|mandib|neck|hyoid/],['thorax',/thorax|abdom|pectoral|rib|heart|lung|liver|stomach|kidney|trunk|back/]])if(re.test(n))return k;return'other';}
// Functional taxonomy from the nomenclature layer: group -> subgroup.
function group(o){return NOM?.taxonomy(o)?.group||'';}
function subgroup(o){return NOM?.taxonomy(o)?.subgroup||'';}
function family(o){const t=NOM?.taxonomy(o);if(t?.group)return t.group;const c=cardFor(o);if(c){if(/^[CTL]\d+$/.test(c.id))return{C:'颈椎',T:'胸椎',L:'腰椎'}[c.id[0]];if(/^rib\d/.test(c.id))return'肋';if(/^costal_cartilage/.test(c.id))return'肋软骨';if(/phalan|metacarp|metatars/.test(c.en.toLowerCase()))return /metacarp/i.test(c.en)?'掌骨':/metatars/i.test(c.en)?'跖骨':'指 / 趾骨';return c.zh;}
 const p=o.collectionPaths?.[0]?.split('/').filter(Boolean)||o.path?.slice(0,-1)||[];return p.slice(-1)[0]||'源模型结构';}
function key(o){const n=names(o);return norm([o.name,o.sourceName,n.zh,n.en,n.la,foldPy(n.py),n.group,n.subgroup,cardFor(o)?.en,region(o),REGIONS[region(o)],...o.path||[],...o.collectionPaths||[]].join(' '));}
function matches(o,q){q=norm(q);if(!q)return true;const text=key(o);return q.split(/\s+/).every(w=>text.includes(w))||LEGACY_TERMS.some(([en,zh])=>zh.includes(q)&&norm(o.name).includes(en));}
const bone=(zh,ids)=>({zh,ids,cat:'skeletal'}),soft=(zh,terms)=>({zh,terms,cat:'joints'});
const JOINTS=[
{id:'shoulder',zh:'肩关节',en:'Glenohumeral joint',region:'upper',type:'球窝关节',related:['scapula','humerus','clavicle','deltoid','supraspinatus','infraspinatus','teres_minor','subscapularis'],parts:[bone('肩胛骨（关节盂侧）',['scapula']),bone('肱骨（肱骨头侧）',['humerus']),soft('关节盂唇',['glenoid labrum']),soft('关节囊与盂肱韧带',['glenohumeral ligament','shoulder capsule','glenohumeral capsule'])],body:'肱骨头与肩胛骨关节盂构成。先看两个相对的骨性区域，再加入盂唇与软组织。关节囊、肩袖与骨性形态共同参与稳定。',motion:'屈伸、收展与旋转。较大的活动范围伴随着对周围软组织稳定作用的依赖。',memory:'先盂后头，再看盂唇与肩袖；活动范围和稳定性要一起记。',sources:['S4','S9'],moving:['humerus']},
{id:'elbow',zh:'肘关节',en:'Elbow joint',region:'upper',type:'复合关节',related:['humerus','ulna','radius','biceps','triceps','brachialis'],parts:[bone('肱骨远端',['humerus']),bone('尺骨近端',['ulna']),bone('桡骨近端',['radius']),soft('桡骨环状韧带',['annular ligament']),soft('尺 / 桡侧副韧带',['ulnar collateral ligament of elbow','radial collateral ligament of elbow'])],body:'把肱尺、肱桡与近侧桡尺三部分放在同一局部观察。骨与关节面必须逐对对应，不能把屈伸和旋转的结构基础混成一个接点。',motion:'肱尺与肱桡部分主要参与屈伸；近侧桡尺关节与远侧桡尺关节共同参与旋前、旋后。',memory:'肱尺记滑车，肱桡记小头；桡尺关系另记旋转。',sources:['S5','S9'],moving:['ulna','radius']},
{id:'radioulnar',zh:'桡尺关节',en:'Radioulnar joints',region:'upper',type:'车轴性连接',related:['radius','ulna'],parts:[bone('桡骨',['radius']),bone('尺骨',['ulna']),soft('环状韧带',['annular ligament']),soft('前臂骨间膜',['interosseous membrane of forearm'])],body:'近侧与远侧桡尺关节应成对学习；前臂骨间膜连接两骨骨间缘。',motion:'在旋前时桡骨与尺骨呈交叉关系；旋后时二者较为平行。运动不能仅由单个局部的静态视图解释。',memory:'近远端共同参与，整体看桡骨相对尺骨的位置。',sources:['S5'],moving:['radius']},
{id:'wrist',zh:'桡腕关节',en:'Radiocarpal joint',region:'upper',type:'椭圆关节',related:['radius','ulna','scaphoid','lunate','triquetrum'],parts:[bone('桡骨远端',['radius']),bone('手舟骨',['scaphoid']),bone('月骨',['lunate']),bone('三角骨',['triquetrum']),soft('关节盘与腕韧带',['articular disc of wrist','radiocarpal ligament'])],body:'从桡骨远端向近排腕骨观察。尺骨与腕骨之间有相关关节盘结构，不能简单理解为尺骨直接与腕骨相接。',motion:'屈伸、桡偏与尺偏；腕的整体活动也与腕骨之间的关节有关。',memory:'近排腕骨由桡侧起：舟、月、三角、豆；豌豆骨不作为桡腕关节的近排关节面成员。',sources:['S5','S8'],moving:['scaphoid','lunate','triquetrum']},
{id:'hip',zh:'髋关节',en:'Hip joint',region:'pelvis',type:'球窝关节',related:['hip','femur','iliacus','psoas_major','gluteus_max'],parts:[bone('髋骨（髋臼）',['hip']),bone('股骨（股骨头）',['femur']),soft('髋臼唇',['acetabular labrum']),soft('髂股 / 耻股 / 坐股韧带',['iliofemoral ligament','pubofemoral ligament','ischiofemoral ligament'])],body:'股骨头与髋臼相接。将髋臼窝、月状面、切迹与髋臼唇分开辨认，再联系关节囊及加强韧带。',motion:'屈伸、收展与旋转。与肩关节比较时，应同时考虑承重、关节窝深度和稳定结构。',memory:'同是球窝，髋重承重与稳定；头、臼、唇、囊逐层看。',sources:['S19','S9'],moving:['femur']},
{id:'knee',zh:'膝关节',en:'Knee joint',region:'lower',type:'胫股＋髌股',related:['femur','tibia','patella','fibula','rectus_femoris','biceps_femoris'],parts:[bone('股骨远端',['femur']),bone('胫骨近端',['tibia']),bone('髌骨',['patella']),soft('内 / 外侧半月板',['medial meniscus','lateral meniscus']),soft('前 / 后交叉韧带',['anterior cruciate ligament','posterior cruciate ligament']),soft('胫 / 腓侧副韧带',['tibial collateral ligament','fibular collateral ligament'])],body:'主要观察胫股和髌股关系。半月板与交叉韧带属于不同种类的稳定与适配结构；不要把腓骨当作胫股关节的关节面组成。',motion:'以屈伸为主，并包含与姿态相关的滚动、滑动和旋转。此工作台的手动单轴演示不模拟完整膝关节运动学。',memory:'骨面配对→半月板→交叉韧带→侧副韧带；逐层隐藏后复述。',sources:['S18','S9'],moving:['tibia','fibula']},
{id:'ankle',zh:'距小腿关节',en:'Talocrural joint',region:'lower',type:'滑车性关节',related:['tibia','fibula','talus','calcaneus'],parts:[bone('胫骨远端',['tibia']),bone('腓骨远端',['fibula']),bone('距骨',['talus']),soft('三角韧带',['deltoid ligament']),soft('外侧韧带群',['anterior talofibular ligament','posterior talofibular ligament','calcaneofibular ligament'])],body:'胫腓骨远端构成的踝穴与距骨滑车相适配。分别查看内踝、外踝与距骨接触区域。',motion:'主要是背屈与跖屈。足的内翻和外翻还涉及距下等其他关节，不等同于踝关节的单轴运动。',memory:'踝记背跖屈；内外翻要联系其他跗骨间关节。',sources:['S18','S9'],moving:['talus','calcaneus']},
{id:'spine',zh:'椎间连接',en:'Intervertebral connections',region:'spine',type:'椎体连接＋关节突关节',related:['L1','L2','L3','L4','L5','C1','C2','C3','C4','C5','C6','C7','T1'],parts:[bone('相邻椎骨',[]),soft('椎间盘',['intervertebral disc','intervertebral disk']),soft('纵韧带与黄韧带',['longitudinal ligament','ligamentum flavum','ligamenta flava'])],body:'将椎体之间的椎间盘连接与关节突之间的滑膜关节分开观察。选择具体椎骨后，优先显示对应的相邻节段。',motion:'不同节段的关节面朝向与活动特点不同；单一旋转轴不能代表整段脊柱的运动。',memory:'前方看椎体与盘，后方看关节突；孔与切迹分别记。',sources:['S3','S8'],moving:[]}
];
const QUESTIONS=[
['肱骨远端哪一结构与尺骨滑车切迹相接？',['肱骨滑车','肱骨小头','大结节','桡窝'],0,'滑车与滑车切迹对应；肱骨小头与桡骨头相接。','humerus',['S5']],
['尺骨头位于尺骨的哪一端？',['近端','远端','骨干中段','鹰嘴内'],1,'尺骨近端以鹰嘴和滑车切迹为显著标志；尺骨头在远端。','ulna',['S5']],
['辨认肱骨前后方向时，哪一窝位于远端后面？',['冠突窝','桡窝','鹰嘴窝','结节间沟'],2,'鹰嘴窝在后，冠突窝与桡窝在前。','humerus',['S5']],
['肩胛骨关节盂与哪一结构相接？',['肱骨头','肱骨滑车','锁骨胸骨端','桡骨头'],0,'关节盂与肱骨头组成肩关节。','scapula',['S4','S9']],
['肩胛冈位于肩胛骨哪一面？',['肋面','背面','关节盂内面','锁骨端'],1,'肩胛冈将背面分为冈上窝和冈下窝。','scapula',['S4']],
['髌骨直接与哪块骨的关节面相接？',['胫骨','腓骨','股骨','髋骨'],2,'髌骨与股骨髌面相关，不直接与胫骨形成关节面。','patella',['S18']],
['股骨粗线主要位于何处？',['股骨体前面','股骨体后面','股骨头关节面','髌面'],1,'先以粗线辨后，再辨认远端髁间窝与前方髌面。','femur',['S18']],
['股骨近端的转子间线与转子间嵴分别主要位于？',['前面与后面','后面与前面','都在前面','都在股骨头内'],0,'转子间线在前，转子间嵴在后。','femur',['S18']],
['闭孔主要由哪些骨性部分围成？',['髂骨与骶骨','坐骨与耻骨','股骨与髋骨','两侧髋骨'],1,'坐骨与耻骨的相关部分围成闭孔。','hip',['S19']],
['相邻椎骨的上下椎切迹共同参与形成什么？',['椎孔','椎间孔','横突孔','骶管裂孔'],1,'椎间孔位于相邻椎骨之间；椎孔由单块椎骨的椎体与椎弓围成。','L4',['S3']],
['椎体之间的典型连接结构是？',['椎间盘','半月板','关节盂唇','桡骨环状韧带'],0,'椎体之间以椎间盘相连；关节突之间是另一类连接。','L3',['S3']],
['寰椎最显著的特点之一是？',['具有粗大的椎体','无典型椎体与棘突','具有长而分叉的齿突','与髋骨组成关节'],1,'寰椎具有前弓、后弓与侧块；齿突属于枢椎。','C1',['S3']],
['齿突属于哪块椎骨？',['寰椎','枢椎','第一胸椎','第五腰椎'],1,'齿突是枢椎的特征结构。','C2',['S3']],
['尺骨是否直接与腕骨形成桡腕关节的关节面接触？',['是，与所有近排腕骨','是，仅与豌豆骨','否，中间有相关关节盘结构','是，仅与大多角骨'],2,'不能将尺骨远端与腕骨关系简化为直接骨面接触。','ulna',['S5']],
['腕骨近排从桡侧到尺侧依次为？',['舟、月、三角、豆','豆、三角、月、舟','大、小、头状、钩','舟、头状、月、钩'],0,'先确定拇指所在的桡侧，再记近排腕骨。','scaphoid',['S5']],
['膝关节胫股部分的骨性配对是？',['股骨与胫骨','股骨与腓骨','胫骨与髌骨','腓骨与髌骨'],0,'胫股与髌股需分开理解；腓骨不是胫股关节面组成。','tibia',['S9','S18']],
['距小腿关节主要完成什么运动？',['背屈与跖屈','仅内翻与外翻','前臂旋前旋后','拇指对掌'],0,'足内外翻还需联系距下等其他关节。','talus',['S9']],
['锁骨的肩峰端与胸骨端相比通常？',['更扁','更粗大且近球形','存在齿突','直接接肱骨头'],0,'锁骨内端较粗大，外端较扁。','clavicle',['S4']],
['胸骨角对应的重要肋软骨定位是？',['第 1 肋软骨','第 2 肋软骨','第 7 肋软骨','第 12 肋软骨'],1,'胸骨柄体交界处的胸骨角用于联系第 2 肋软骨。','sternum',['S20']],
['肱二头肌止点的重要骨性结构是？',['尺骨鹰嘴','桡骨粗隆','肱骨大结节','股骨小转子'],1,'肱二头肌止于桡骨粗隆，并经腱膜与前臂筋膜联系。','biceps',['S12']],
['肱三头肌与哪项运动关系最直接？',['伸肘','屈腕','拇指对掌','足背屈'],0,'肱三头肌是伸肘的重要肌，止于尺骨鹰嘴。','triceps',['S12']],
['解剖学“关节面”与“关节突”的关系更准确的是？',['二者完全同义','关节面是特定接触表面，关节突是骨性突起','关节突一定是软骨','关节面一定是独立骨'],1,'结构实体与其上的表面区域属于不同描述层级。','L4',['S3']],
['仅有骨的外表面网格，裁切后可以可靠得到？',['源表面与切面的交线','患者真实骨髓信号','完整骨小梁显微结构','全部血管分支'],0,'外表面交线不能代替 CT / MRI 体数据或内部组织网格。','humerus',[]],
['手的第一指通常具有几节指骨？',['1','2','3','4'],1,'拇指有近、远两节；其余手指通常有三节。','metacarpal1',['S5']],
['肩、髋关节比较，首先应该同时考虑什么？',['活动范围与稳定结构','仅模型颜色','仅源文件大小','只有关节名称'],0,'关节窝形态、关节囊、韧带与肌的作用要结合运动范围理解。','hip',['S9']]
].map((q,i)=>({id:'q'+i,question:q[0],options:q[1],answer:q[2],explanation:q[3],subject:q[4],sources:q[5]}));
window.FormaKnowledge={cards,byId,sources:data.sources,cardFor,title,names,englishName,pinyin,prettyEn,side,region,family,group,subgroup,nomId,nomStatus,key,matches,JOINTS,QUESTIONS,norm,cleanName,LEGACY_TERMS};
})();
