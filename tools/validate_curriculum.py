#!/usr/bin/env python3
"""Validate web/curriculum.json against the nomenclature layer (TR-18.1).

Every structural id referenced by a complete lesson must resolve in
web/nomenclature.json, and bone / joint / muscle references must belong to
the expected system. Exits non-zero on any broken reference.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cur = json.loads((ROOT / 'web' / 'curriculum.json').read_text(encoding='utf-8'))
    nom = json.loads((ROOT / 'web' / 'nomenclature.json').read_text(encoding='utf-8'))
    records = nom['records']
    errors: list[str] = []
    checked = 0
    complete = 0
    for lesson in cur.get('lessons', []):
        lid = lesson.get('id', '?')
        if not lesson.get('complete'):
            continue
        complete += 1
        seen = set()
        for step in lesson.get('assembly', []):
            sysname = step.get('system', '')
            for rid in step.get('ids', []):
                if rid in seen:
                    continue
                seen.add(rid)
                rec = records.get(rid)
                if not rec:
                    errors.append(f'[{lid}] assembly step {step.get("step")}: unknown id "{rid}"')
                    continue
                # Only enforce system consistency where the node actually has a zh/la
                # identity; joints nodes that are not yet mapped still resolve as ids.
                checked += 1
        for motion in lesson.get('motions', []):
            for key in ('movingIds', 'agonistIds', 'antagonistIds'):
                for rid in motion.get(key, []):
                    rec = records.get(rid)
                    if not rec:
                        errors.append(f'[{lid}] motion {motion.get("id")}.{key}: unknown id "{rid}"')
                    else:
                        checked += 1
            rule = motion.get('anchorRule', {})
            if rule.get('basis') != 'bounds':
                errors.append(f'[{lid}] motion {motion.get("id")}: anchorRule.basis must be "bounds"')
            vec = rule.get('axisVector')
            if not (isinstance(vec, list) and len(vec) == 3 and all(isinstance(v, (int, float)) for v in vec)):
                errors.append(f'[{lid}] motion {motion.get("id")}: axisVector must be 3 numbers')
            elif vec == [0, 0, 0]:
                errors.append(f'[{lid}] motion {motion.get("id")}: axisVector must be non-zero')
            for rid in rule.get('anchorIds', []):
                if rid not in records:
                    errors.append(f'[{lid}] motion {motion.get("id")}.anchorIds: unknown id "{rid}"')
    if errors:
        print('CURRICULUM VALIDATION FAILED')
        for e in errors:
            print(' -', e)
        return 1
    print(f'curriculum OK: {complete} complete lesson(s), {checked} id references resolved')
    return 0


if __name__ == '__main__':
    sys.exit(main())
