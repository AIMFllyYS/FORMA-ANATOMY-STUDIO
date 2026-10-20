#!/usr/bin/env python3
"""Build the nomenclature layer for upstream GLB node names.

Pipeline (all network responses cached under tools/data/cache, reruns offline):
  1. tools/data/node_corpus.json            — actual mesh nodes per system
  2. TA2.csv (Z-Anatomy, CC BY-SA)           — English/Latin canonical names
  3. Wikidata SPARQL (CC0)                   — zh/la labels, FMA/TA98/TA2 ids
  4. web/knowledge.json cards                — existing zh names (bridge)
  5. tools/data/nomenclature_review_zh.csv   — manual zh names + functional groups
  6. tools/data/zh_proofread.json            — curated zh (wins over Wikidata and the CSV)

Outputs:
  web/nomenclature.json                      — runtime identity records + assignments
  tools/data/nomenclature_coverage.json/.md  — coverage report

Auto-derived zh is always status=pending. The review CSV and
tools/data/zh_proofread.json are the reviewed sources; the proof table wins
on the Chinese name. Unmatched nodes stay unmatched (runtime keeps the source name).
"""
from __future__ import annotations
import argparse, csv, io, json, re, time, urllib.parse, urllib.request
from pathlib import Path
try:
    from opencc import OpenCC
    _t2s = OpenCC('t2s').convert
except ImportError:  # 构建期可选依赖：pip install -r tools/requirements.txt
    print('警告：未安装 opencc-python-reimplemented，Wikidata 繁体中文将不转换；见 tools/requirements.txt')
    _t2s = lambda s: s

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tools' / 'data'
CACHE = DATA / 'cache'
CORPUS = DATA / 'node_corpus.json'
REVIEW_CSV = DATA / 'nomenclature_review_zh.csv'
PROOF_JSON = DATA / 'zh_proofread.json'
TA2_URL = 'https://raw.githubusercontent.com/Z-Anatomy/Models-of-human-anatomy/master/TA2.csv'
UA = 'FormaAnatomyBuilder/4.0 (open-source educational anatomy workbench)'
SPARQL = 'https://query.wikidata.org/sparql'
BATCH = 80
SLEEP = 1.2

SYSTEM_ORDER = ['skeletal', 'joints', 'muscles', 'nerves', 'organs', 'vessels', 'lymph']


def http(url: str, data: bytes | None = None, accept='application/json') -> bytes:
    headers = {'User-Agent': UA, 'Accept': accept}
    if data is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def cache_bytes(name: str, url: str, data: bytes | None = None, accept='application/json') -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / name
    if not p.exists():
        p.write_bytes(http(url, data, accept))
    return p.read_bytes()


# ---------- name normalisation ----------
def norm(en: str) -> str:
    s = en.lower().strip()
    s = re.sub(r'[._-]', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s


STOP_PARTS = ['left', 'right', 'l', 'r']


def variants(name: str) -> list[str]:
    """Wikidata label variants for one node base name."""
    n = norm(name)
    toks = n.split(' ')
    out = {n}
    if 'muscle' in toks:
        no_m = ' '.join(t for t in toks if t != 'muscle')
        if no_m:
            out.add(no_m)
    elif n and not n.endswith(('artery', 'vein', 'nerve', 'ligament', 'bone', 'duct', 'gland', 'fascia', 'tendon', 'membrane', 'cartilage', 'joint', 'valve')):
        out.add(n + ' muscle')
    return [v for v in out if v]


def slug(en: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '_', norm(en)).strip('_')
    return s[:96] or 'unnamed'


# ---------- TA2 ----------
def load_ta2() -> dict[str, dict]:
    raw = cache_bytes('TA2.csv', TA2_URL, accept='text/csv').decode('utf-8-sig')
    out = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or ';' not in line:
            continue
        parts = [p.strip().strip('"') for p in line.split(';')]
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        ta2id, en, la = parts[0], parts[1], parts[2]
        if en:
            out.setdefault(norm(en), {'ta2': ta2id, 'en': en, 'la': la or ''})
    return out


# ---------- Wikidata ----------
SPARQL_TMPL = '''SELECT ?input ?item
  (GROUP_CONCAT(DISTINCT ?en; separator=" | ") AS ?enLabel)
  (GROUP_CONCAT(DISTINCT ?la; separator=" | ") AS ?laLabel)
  (GROUP_CONCAT(DISTINCT ?zh; separator=" | ") AS ?zhLabel)
  (GROUP_CONCAT(DISTINCT ?fma; separator=" | ") AS ?fmaID)
  (GROUP_CONCAT(DISTINCT ?ta98; separator=" | ") AS ?ta98ID)
  (GROUP_CONCAT(DISTINCT ?ta2id; separator=" | ") AS ?ta2ID)
WHERE {
  VALUES ?input { %s }
  ?item rdfs:label|skos:altLabel ?input .
  OPTIONAL { ?item rdfs:label ?en FILTER(LANG(?en)="en") }
  OPTIONAL { ?item rdfs:label ?la FILTER(LANG(?la)="la") }
  OPTIONAL { ?item rdfs:label ?zh FILTER(LANG(?zh) IN ("zh","zh-cn","zh-hans","zh-hant")) }
  OPTIONAL { ?item wdt:P1402 ?fma }
  OPTIONAL { ?item wdt:P1323 ?ta98 }
  OPTIONAL { ?item wdt:P7173 ?ta2id }
} GROUP BY ?input ?item'''


def wikidata_lookup(names: list[str]) -> dict[str, list[dict]]:
    """name -> candidate rows. Cached per batch file keyed on its value hash."""
    import hashlib
    result: dict[str, list[dict]] = {n: [] for n in names}
    uniq = list(dict.fromkeys(names))
    for i in range(0, len(uniq), BATCH):
        chunk = uniq[i:i + BATCH]
        values = ' '.join(f'"{v.replace(chr(34), "")}"@en' for v in chunk)
        q = SPARQL_TMPL % values
        key = 'wd_' + hashlib.sha1(q.encode()).hexdigest()[:16] + '.json'
        if not (CACHE / key).exists():
            body = urllib.parse.urlencode({'query': q}).encode()
            try:
                cache_bytes(key, SPARQL, data=body)
            except Exception as e:
                print(f'  Wikidata 批次 {i // BATCH + 1} 失败：{e}')
                continue
            time.sleep(SLEEP)
        data = json.loads((CACHE / key).read_text(encoding='utf-8'))
        for b in data.get('results', {}).get('bindings', []):
            def g(k):
                return b.get(k, {}).get('value', '')
            result.setdefault(g('input'), []).append({
                'item': g('item'), 'en': g('enLabel'), 'la': g('laLabel'),
                'zh': [z for z in g('zhLabel').split(' | ') if z],
                'fma': [x for x in g('fmaID').split(' | ') if x],
                'ta98': [x for x in g('ta98ID').split(' | ') if x],
                'ta2': [x for x in g('ta2ID').split(' | ') if x],
            })
    return result


def pick_candidate(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    # 有标准 id 者优先；其次有拉丁名；同一实体多行合并后取 zh 最短（常用名）
    def score(r):
        return (len(r['fma']) + len(r['ta98']) + len(r['ta2']), 1 if r['la'] else 0)
    best = max(rows, key=score)
    if not (best['fma'] or best['ta98'] or best['ta2'] or best['la']):
        return None
    return best


# ---------- manual review ----------
def load_proof() -> dict[str, dict]:
    """Curated zh keyed by normalised English. Applied last so rebuilds keep it."""
    if not PROOF_JSON.exists():
        return {}
    data = json.loads(PROOF_JSON.read_text(encoding='utf-8'))
    out = {}
    for row in data.get('entries', []):
        key = norm(row.get('en', ''))
        if key and (row.get('zh') or '').strip():
            out[key] = row
    return out


def load_review() -> dict[str, dict]:
    if not REVIEW_CSV.exists():
        return {}
    out = {}
    with REVIEW_CSV.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            key = norm(row.get('en', ''))
            if key:
                out[key] = {k: (v or '').strip() for k, v in row.items()}
    return out


# ---------- coarse functional group heuristics (refined by review CSV) ----------
REGION_RULES = [
    ('head', r'head|neck|cervic|cephal|cranio|skull|face|facial|masseter|temporalis|pharyng|laryng|hyoid|tongue|scalen'),
    ('upper', r'humer|brachii|brachial|ulnar|radial|carp|manual|hand|digit|pollic|deltoid|pectoral|supraspin|infraspin|teres|subscapular|latissimus|coracobrachialis|biceps|triceps|anconeus|pronator|supinator|flexor carpi|extensor carpi|lumbrical|interosse|thenar|hypothenar|serratus anterior|levator scapulae|rhomboid|trapezius|omohyoid'),
    ('lower', r'glute|femor|quadriceps|vastus|sartorius|adductor|hamstring|biceps femoris|semitendinosus|semimembranosus|gastrocnemius|soleus|tibial|fibular|peroneal|calcane|plantar|halluc|popliteus|psoas|iliacus|pectineus|gracilis|obturator|gemellus|piriformis|quadratus femoris|extensor digitorum (longus|brevis)|flexor digitorum (longus|brevis)'),
    ('thorax', r'thorac|intercostal|diaphragm|abdomin|oblique|rectus abdominis|transversus|pyramidalis|inguinal|linea alba|pectineal|levator ani|perine|coccyg|sphincter|urogenital|pelvic'),
    ('spine', r'iliocostalis|longissimus|spinalis|semispinalis|multifidus|rotator|splenius|erector spinae|quadratus lumborum'),
]


def guess_region(en: str) -> str:
    n = norm(en)
    for region, pat in REGION_RULES:
        if re.search(pat, n):
            return region
    return 'other'


# ---------- functional taxonomy (auto; manual review CSV always wins) ----------
# Ordered (regex, group, subgroup, region). First hit wins. Region uses the
# runtime REGIONS keys: head / spine / thorax / upper / pelvis / lower / other.
def _rule(pat, group, subgroup, region='other'):
    return (re.compile(pat), group, subgroup, region)


MUSCLE_RULES = [
    # 眼球外肌归感觉器
    _rule(r'rectus muscle|oblique muscle|tendinous ring|trochlea of superior oblique', '感觉器', '眼球外肌', 'head'),
    # 头颈肌
    _rule(r'temporalis|pterygoid|masseter', '头颈肌', '咀嚼肌', 'head'),
    _rule(r'genioglossus|hyoglossus|styloglossus|palatoglossus|tongue', '头颈肌', '舌肌', 'head'),
    _rule(r'pharyngeal constrictor|stylopharyngeus|palatopharyngeus|salpingopharyngeus', '头颈肌', '咽肌', 'head'),
    _rule(r'arytenoid|crico(thyroid|arytenoid)|thyroarytenoid|vocalis|laryngeal', '头颈肌', '喉肌', 'head'),
    _rule(r'geniohyoid|mylohyoid|stylohyoid|digastric', '头颈肌', '舌骨上肌群', 'head'),
    _rule(r'sternohyoid|omohyoid|sternothyroid|thyrohyoid', '头颈肌', '舌骨下肌群', 'head'),
    _rule(r'longus (colli|capitis)|rectus capitis|scalen', '头颈肌', '椎前与斜角肌群', 'head'),
    _rule(r'sternocleidomastoid', '头颈肌', '颈浅肌群', 'head'),
    _rule(r'frontalis|occipitalis|temporoparietalis|procerus|nasalis|zygomaticus|risorius|mentalis|orbicularis|labii|depressor|levator.*anguli|buccinator|corrugator|facial', '头颈肌', '面肌（表情肌）', 'head'),
    # 躯干肌
    _rule(r'splenius|semispinalis|longissimus|iliocostalis|spinalis|multifidus|rotator|erector spinae', '躯干肌', '背深肌', 'spine'),
    _rule(r'trapezius|latissimus dorsi|levator scapulae|rhomboid|serratus posterior', '躯干肌', '背浅肌', 'thorax'),
    _rule(r'quadratus lumborum', '躯干肌', '背深肌', 'thorax'),
    _rule(r'intercostal|transversus thoracis|subcostalis|levator costarum', '躯干肌', '胸壁肌', 'thorax'),
    _rule(r'^diaphragm$|diaphragm muscle', '躯干肌', '膈', 'thorax'),
    _rule(r'rectus abdominis|pyramidalis|abdominal oblique|transversus abdominis|linea alba|inguinal ligament|transversalis fascia', '躯干肌', '腹肌与腹筋膜', 'thorax'),
    _rule(r'pectoral fascia|clavipectoral fascia', '躯干肌', '胸筋膜', 'thorax'),
    # 盆底与会阴
    _rule(r'coccygeus|pubococcygeus|iliococcygeus|levator ani|anal sphincter|perine|urogenital|bulbospongiosus|ischiocavernosus', '盆底与会阴肌', '盆膈与会阴', 'pelvis'),
    # 上肢带与连接
    _rule(r'deltoid|supraspinatus|infraspinatus|teres (major|minor)|subscapularis', '上肢带肌与肩肌', '肩肌', 'upper'),
    _rule(r'pectoralis|serratus anterior|subclavius', '上肢带肌与肩肌', '胸肌连接部', 'upper'),
    # 臂肌
    _rule(r'biceps|coracobrachialis|brachialis muscle', '臂肌', '前群', 'upper'),
    _rule(r'triceps|anconeus', '臂肌', '后群', 'upper'),
    # 前臂肌
    _rule(r'brachioradialis|pronator|palmaris longus|flexor carpi|flexor digitorum (superficialis|profundus)|flexor pollicis longus|flexor digitorum profundus', '前臂肌', '前群', 'upper'),
    _rule(r'extensor carpi|extensor digitorum|extensor digiti minimi|extensor indicis|extensor pollicis|abductor pollicis longus|supinator|extensor carpi ulnaris|anconeus', '前臂肌', '后群', 'upper'),
    # 手肌
    _rule(r'abductor pollicis brevis|opponens pollicis|flexor pollicis brevis|adductor pollicis|thenar', '手肌', '鱼际肌群', 'upper'),
    _rule(r'abductor digiti minimi of hand|opponens digiti minimi|flexor digiti minimi brevis|hypothenar', '手肌', '小鱼际肌群', 'upper'),
    _rule(r'lumbrical muscles of hand', '手肌', '蚓状肌', 'upper'),
    _rule(r'interossei muscles of hand|palmar interossei|dorsal interossei', '手肌', '骨间肌', 'upper'),
    # 上肢筋膜/腱鞘/支持带/腱膜
    _rule(r'palmar aponeurosis', '上肢筋膜滑膜囊与腱鞘', '掌腱膜', 'upper'),
    _rule(r'retinaculum of wrist|carpal tunnel|bursa.*(wrist|hand|elbow|shoulder)|synovial sheath.*(hand|wrist|finger)|digital sheath|vagina', '上肢筋膜滑膜囊与腱鞘', '腕手部支持带与腱鞘', 'upper'),
    # 髋肌
    _rule(r'psoas|iliacus muscle|iliopsoas', '髋肌', '髂腰肌（前群）', 'pelvis'),
    _rule(r'gluteus|tensor fasciae latae', '髋肌', '臀肌', 'lower'),
    _rule(r'piriformis|obturator (internus|externus)|quadratus femoris|gemellus|sacrospinalis', '髋肌', '臀深肌（外旋肌）', 'lower'),
    # 大腿肌
    _rule(r'sartorius|rectus femoris|vastus|quadriceps', '大腿肌', '前群', 'lower'),
    _rule(r'gracilis|pectineus|adductor', '大腿肌', '内侧群', 'lower'),
    _rule(r'biceps femoris|semitendinosus|semimembranosus|hamstring', '大腿肌', '后群（腘绳肌）', 'lower'),
    _rule(r'iliotibial tract|fascia lata', '下肢筋膜滑膜囊与腱鞘', '大腿筋膜', 'lower'),
    # 小腿肌
    _rule(r'tibialis anterior|extensor digitorum longus|extensor hallucis longus|fibularis tertius|peroneus tertius', '小腿肌', '前群', 'lower'),
    _rule(r'fibularis (longus|brevis)|peroneus (longus|brevis)', '小腿肌', '外侧群', 'lower'),
    _rule(r'gastrocnemius|soleus|plantaris|popliteus|tibialis posterior|flexor digitorum longus|flexor hallucis longus', '小腿肌', '后群', 'lower'),
    _rule(r'crural fascia|calcaneal tendon|achilles', '下肢筋膜滑膜囊与腱鞘', '小腿筋膜与跟腱', 'lower'),
    _rule(r'retinaculum of ankle|malleolar retinaculum', '下肢筋膜滑膜囊与腱鞘', '踝部支持带', 'lower'),
    # 足肌
    _rule(r'extensor digitorum brevis|extensor hallucis brevis', '足肌', '足背肌', 'lower'),
    _rule(r'abductor hallucis|flexor hallucis brevis|adductor hallucis', '足肌', '拇趾肌群', 'lower'),
    _rule(r'abductor digiti minimi.*foot|flexor digiti minimi brevis.*foot|opponens digiti minimi.*foot', '足肌', '小趾肌群', 'lower'),
    _rule(r'lumbrical.*foot', '足肌', '蚓状肌', 'lower'),
    _rule(r'plantar interossei|dorsal interossei.*foot', '足肌', '骨间肌', 'lower'),
    _rule(r'flexor digitorum brevis|quadratus plantae|plantar aponeurosis|plantar fascia', '足肌', '足底肌与腱膜', 'lower'),
]

# 内脏按系统解剖学九大系统归组
ORGAN_RULES = [
    _rule(r'trachea|epiglottis|bronch|lobe of (left|right) lung|lung|pleura|larynx(?!.*muscle)', '内脏·呼吸系统', '呼吸道与肺', 'thorax'),
    _rule(r'kidney|renal pelvis|ureter|urinary bladder|urethra', '内脏·泌尿系统', '泌尿器官', 'pelvis'),
    _rule(r'testis|epididymis|ductus deferens|ejaculatory duct|prostate|seminal gland|corpus (cavernosum|spongiosum)|glans penis|penis|scrotum', '内脏·生殖系统', '男性生殖器官', 'pelvis'),
    _rule(r'ovary|uterus|vagina|uterine|fallopian|clitoris|labium|mammary', '内脏·生殖系统', '女性生殖器官', 'pelvis'),
    _rule(r'thyroid|parathyroid|suprarenal|adrenal|pineal|hypophysis|pituitary|thymus|isthmus', '内脏·内分泌系统', '内分泌腺', 'head'),
    _rule(r'pharynx|nasopharynx|oropharynx|laryngopharynx', '内脏·消化系统', '咽', 'head'),
    _rule(r'o?esophagus|stomach|duodenum|jejunum|ileum|caecum|cecum|colon|vermiform appendix|rectum|anal canal|taenia|mucosa of stomach', '内脏·消化系统', '消化管', 'thorax'),
    _rule(r'liver|hepatic|gallbladder|gall bladder|bile duct|pancrea|salivary|parotid|submandibular|sublingual|gingiva|tongue|soft palate|uvula|palatine|bile', '内脏·消化系统', '消化腺与口咽', 'head'),
    _rule(r'omentum|mesentery|mesocolon|meso-appendix|peritoneum|peritoneal', '内脏·消化系统', '腹膜与系膜', 'thorax'),
    _rule(r'nasal|nose|concha|eye|ocular|eyeball|cornea|retina|lens', '感觉器', '视器与嗅器', 'head'),
]


def muscle_taxonomy(en: str):
    n = norm(en)
    for rx, group, subgroup, region in MUSCLE_RULES:
        if rx.search(n):
            return group, subgroup, region
    return None


def organ_taxonomy(en: str):
    n = norm(en)
    for rx, group, subgroup, region in ORGAN_RULES:
        if rx.search(n):
            return group, subgroup, region
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--systems', default=','.join(SYSTEM_ORDER))
    ap.add_argument('--no-wikidata', action='store_true')
    a = ap.parse_args()
    wanted = [s for s in a.systems.split(',') if s in SYSTEM_ORDER]

    corpus = json.loads(CORPUS.read_text(encoding='utf-8'))['systems']
    ta2 = load_ta2()
    review = load_review()
    proof = load_proof()
    cards = json.loads((ROOT / 'web' / 'knowledge.json').read_text(encoding='utf-8'))['cards']
    card_zh = {}
    for c in cards:
        if c.get('zh') and c.get('en'):
            card_zh.setdefault(norm(c['en']), c['zh'])

    # unique mesh node base names per systems requested
    nodes = []
    for s in wanted:
        for n in corpus[s]['nodes']:
            if n['hasMesh'] and not n['special']:
                nodes.append({'system': s, **n})
    unique = {}
    for n in nodes:
        unique.setdefault(norm(n['name']), n['name'])

    wd = {} if a.no_wikidata else wikidata_lookup(list(unique.keys()))

    records: dict[str, dict] = {}
    assignments = []
    stats = {}

    def get_record(en_name: str, system: str = ''):
        key = norm(en_name)
        rid = slug(en_name)
        existing = records.get(rid)
        if existing:
            if not existing.get('group'):
                tax = muscle_taxonomy(en_name) if system == 'muscles' else organ_taxonomy(en_name) if system == 'organs' else None
                if tax:
                    existing['group'], existing['subgroup'], tax_region = tax
                    if tax_region and not existing.get('region'):
                        existing['region'] = tax_region
            return rid
        rec = {'id': rid, 'en': en_name, 'la': '', 'zh': '', 'region': '', 'group': '', 'subgroup': '',
               'method': 'none', 'status': 'unmatched', 'sources': {}}
        # 1 manual review
        rv = review.get(key)
        cand = None
        if rv:
            rec['zh'] = rv.get('zh', '')
            if rv.get('la'):
                rec['la'] = rv['la']
            rec['region'] = rv.get('region', '')
            rec['group'] = rv.get('group', '')
            rec['subgroup'] = rv.get('subgroup', '')
            if rv.get('ta2'):
                rec['sources']['ta2'] = rv['ta2']
            rec['method'] = 'manual'
            rec['status'] = 'reviewed' if rv.get('status', 'reviewed') == 'reviewed' else 'pending'
        # 2 TA2 latin
        t = ta2.get(key)
        if t:
            if not rec['la']:
                rec['la'] = t['la']
            rec['sources'].setdefault('ta2', t['ta2'])
        # 3 wikidata
        if not a.no_wikidata:
            cand = pick_candidate(wd.get(key)) or pick_candidate([c for v in variants(en_name) for c in wd.get(v, [])])
            if cand:
                if not rec['zh'] and cand['zh']:
                    rec['zh'] = _t2s(cand['zh'][0]).strip()
                    if rec['method'] == 'none':
                        rec['method'] = 'wikidata'
                        rec['status'] = 'pending'
                if not rec['la'] and cand['la']:
                    rec['la'] = cand['la'].split(' | ')[0]
                rec['sources']['wikidata'] = cand['item'].rsplit('/', 1)[-1]
                if cand['fma']:
                    rec['sources']['fma'] = cand['fma'][0]
                if cand['ta98']:
                    rec['sources']['ta98'] = cand['ta98'][0]
                if cand['ta2'] and 'ta2' not in rec['sources']:
                    rec['sources']['ta2'] = cand['ta2'][0]
        # 4 knowledge card bridge
        if not rec['zh'] and key in card_zh:
            rec['zh'] = card_zh[key]
            if rec['method'] == 'none':
                rec['method'] = 'card'
                rec['status'] = 'pending'
        # Auto functional taxonomy. Never overrides manual review; only fills
        # empty group/subgroup and keeps method/status untouched.
        if not rec['group']:
            tax = None
            if system == 'muscles':
                tax = muscle_taxonomy(en_name)
            elif system == 'organs':
                tax = organ_taxonomy(en_name)
            if tax:
                rec['group'], rec['subgroup'], tax_region = tax
                if tax_region and not rec['region']:
                    rec['region'] = tax_region
        if not rec['region']:
            rec['region'] = guess_region(en_name)
        # Curated proof table wins over Wikidata, cards and the older review CSV
        # for the Chinese name. Groups from the CSV are left in place.
        pv = proof.get(key)
        if pv and pv.get('zh'):
            rec['zh'] = pv['zh'].strip()
            rec['method'] = 'manual'
            rec['status'] = 'reviewed' if pv.get('status') == 'reviewed' else 'pending'
        records[rid] = rec
        return rid

    for n in nodes:
        rid = get_record(n['name'], n['system'])
        rec = records[rid]
        st = stats.setdefault(n['system'], {'total': 0, 'zh': 0, 'reviewed': 0, 'methods': {}})
        st['total'] += 1
        if rec['zh']:
            st['zh'] += 1
        if rec['status'] == 'reviewed':
            st['reviewed'] += 1
        st['methods'][rec['method']] = st['methods'].get(rec['method'], 0) + 1
        assignments.append({'system': n['system'], 'nodeIndex': n['nodeIndex'], 'name': n['name'],
                            'side': n['side'], 'id': rid if rec['zh'] or rec['la'] else None,
                            'method': rec['method'], 'status': rec['status'], 'zh': rec['zh']})

    out = {'version': 1, 'generatedWith': 'tools/build_nomenclature.py',
           'recordCount': len(records),
           'records': records, 'assignments': assignments}
    (ROOT / 'web').mkdir(exist_ok=True)
    (ROOT / 'web' / 'nomenclature.json').write_text(
        json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    # coverage report
    lines = ['# 命名覆盖率报告', '', '| 系统 | 网格节点 | 有中文名 | 覆盖率 | 已审校 | 方法分布 |', '| --- | ---: | ---: | ---: | ---: | --- |']
    cov = {'systems': {}}
    for s in wanted:
        st = stats.get(s, {'total': 0, 'zh': 0, 'reviewed': 0, 'methods': {}})
        pct = round(100 * st['zh'] / st['total'], 1) if st['total'] else 0
        cov['systems'][s] = {**st, 'coverage': pct}
        lines.append(f"| {s} | {st['total']} | {st['zh']} | {pct}% | {st['reviewed']} | {st['methods']} |")
    mus_org = [stats.get(s) for s in ('muscles', 'organs') if stats.get(s)]
    tot = sum(x['total'] for x in mus_org)
    zh = sum(x['zh'] for x in mus_org)
    cov['muscles_organs_coverage'] = round(100 * zh / tot, 1) if tot else 0
    lines += ['', f"**肌肉+内脏合计覆盖率：{cov['muscles_organs_coverage']}%（目标 ≥90%）**"]
    (DATA / 'nomenclature_coverage.json').write_text(json.dumps(cov, ensure_ascii=False, indent=2), encoding='utf-8')
    (DATA / 'nomenclature_coverage.md').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))
    print(f"\nrecords={len(records)} → web/nomenclature.json")


if __name__ == '__main__':
    main()
