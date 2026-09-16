#!/usr/bin/env python3
"""Extract mesh-node name corpus from the seven upstream system GLBs.

Standard library only. Downloads the compact browser GLBs (same sources as
web/core.js), reads only the glTF JSON chunk (BIN ignored), and writes
tools/data/node_corpus.json — the baseline for nomenclature coverage work.

Z-Anatomy naming conventions recorded per node:
  - trailing .l / .r   : anatomical side
  - trailing .j        : empty/join marker object (no geometry expected)
  - trailing .g        : 3D text object
  - trailing apostrophe: marked "not modelled" upstream
No GLB binaries are committed (tools/data/cache is git-ignored).
"""
from __future__ import annotations
import argparse, json, re, struct, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'tools' / 'data' / 'cache'
OUT = ROOT / 'tools' / 'data' / 'node_corpus.json'
BASES = [
    'https://raw.githubusercontent.com/DrMuratAltun/anatomi-simulatoru/refs/heads/main/systems/',
    'https://drmurataltun.github.io/anatomi-simulatoru/systems/',
]
SYSTEMS = {
    'skeletal': 'iskelet.glb',
    'joints': 'eklem.glb',
    'muscles': 'kas.glb',
    'nerves': 'sinir.glb',
    'organs': 'ic-organlar.glb',
    'vessels': 'dolasim.glb',
    'lymph': 'lenf.glb',
}
SIDE_RE = re.compile(r'[._-]([lrb])$', re.IGNORECASE)
SPECIAL_RE = re.compile(r"[._-]([jg])$")


def fetch(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'Forma corpus extractor/4.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_glb(system: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f'{system}.glb'
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    name = SYSTEMS[system]
    last_err = None
    for base in BASES:
        try:
            data = fetch(base + name)
            if len(data) < 1000 or data[:4] != b'glTF':
                raise ValueError('downloaded payload is not a GLB')
            dest.write_bytes(data)
            return dest
        except Exception as e:  # try mirror
            last_err = e
    raise SystemExit(f'无法下载 {name}: {last_err}')


def gltf_json(raw: bytes) -> dict:
    if len(raw) < 20 or struct.unpack_from('<I', raw, 0)[0] != 0x46546C67:
        raise ValueError('not a GLB')
    length = struct.unpack_from('<I', raw, 8)[0]
    off = 12
    while off + 8 <= length:
        size, ctype = struct.unpack_from('<II', raw, off)
        off += 8
        if ctype == 0x4E4F534A:
            return json.loads(raw[off:off + size].decode('utf-8').rstrip('\x00 '))
        off += size
    raise ValueError('GLB JSON chunk missing')


def classify(name: str) -> tuple[str, str]:
    n = name.strip()
    special = ''
    if n.endswith("'"):
        special = 'not_modelled_marker'
        n = n[:-1].strip()
    m = SPECIAL_RE.search(n)
    if m:
        special = {'j': 'empty_marker', 'g': 'text_object'}[m.group(1).lower()]
        n = n[:m.start()].rstrip(' ._-')
    side = ''
    m = SIDE_RE.search(n)
    if m:
        side = {'l': 'L', 'r': 'R', 'b': ''}[m.group(1).lower()]
        n = n[:m.start()].rstrip(' ._-')
    return n, side, special  # type: ignore[return-value]


def extract(system: str) -> dict:
    gltf = gltf_json(get_glb(system).read_bytes())
    nodes = gltf.get('nodes', [])
    roots = (gltf.get('scenes', [{}])[gltf.get('scene', 0)].get('nodes')
             if gltf.get('scenes') else [])
    if not roots:
        roots = [i for i, n in enumerate(nodes) if not any(i in (c.get('children') or []) for c in nodes)]
    seen: set[int] = set()
    entries = []

    def visit(i: int, path: list[str]):
        if i in seen:
            return
        seen.add(i)
        node = nodes[i]
        name = node.get('name', f'未命名节点 {i}')
        base, side, special = classify(name)
        primitives = 0
        if node.get('mesh') is not None:
            mesh = gltf.get('meshes', [{}])[node['mesh']] if node['mesh'] < len(gltf.get('meshes', [])) else {}
            primitives = len(mesh.get('primitives', []))
        extras = node.get('extras') or {}
        entries.append({
            'nodeIndex': i,
            'name': base,
            'rawName': name,
            'side': side,
            'special': special,
            'hasMesh': node.get('mesh') is not None,
            'primitives': primitives,
            'collectionPaths': extras.get('collection_paths') or [],
        })
        for c in node.get('children') or []:
            visit(c, path + [name])

    for r in roots:
        visit(r, [])
    mesh_nodes = [e for e in entries if e['hasMesh'] and not e['special']]
    sides = {}
    for e in mesh_nodes:
        sides[e['side']] = sides.get(e['side'], 0) + 1
    return {
        'system': system,
        'file': SYSTEMS[system],
        'asset': gltf.get('asset', {}),
        'totalNodes': len(entries),
        'meshNodes': len(mesh_nodes),
        'specialNodes': {
            'emptyMarker': sum(1 for e in entries if e['special'] == 'empty_marker'),
            'textObject': sum(1 for e in entries if e['special'] == 'text_object'),
            'notModelled': sum(1 for e in entries if e['special'] == 'not_modelled_marker'),
        },
        'sideCount': sides,
        'nodes': entries,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--systems', default=','.join(SYSTEMS), help='comma-separated subset')
    a = ap.parse_args()
    wanted = [s.strip() for s in a.systems.split(',') if s.strip() in SYSTEMS]
    if not wanted:
        ap.error('no valid systems selected')
    corpus = {'version': 1, 'generatedWith': 'tools/extract_node_corpus.py', 'systems': {}}
    for s in wanted:
        print(f'提取 {s} ({SYSTEMS[s]}) …', flush=True)
        corpus['systems'][s] = extract(s)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(corpus, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    total = sum(x['meshNodes'] for x in corpus['systems'].values())
    print(f'\n已写入 {OUT.relative_to(ROOT)}（{total} 个网格节点）')
    for s, x in corpus['systems'].items():
        print(f"  {s:9s} 网格 {x['meshNodes']:4d} / 节点 {x['totalNodes']:4d}  侧别 {x['sideCount']}  特殊 {x['specialNodes']}")


if __name__ == '__main__':
    main()
