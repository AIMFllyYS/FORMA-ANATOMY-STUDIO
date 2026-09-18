// 从真实 app.js 提取 layoutLabels 并验证防遮挡几何性质（不复制算法，避免测到假实现）。
import { readFileSync } from 'node:fs';
const src = readFileSync(new URL('../web/app.js', import.meta.url), 'utf8');
const start = src.indexOf('function layoutLabels');
const end = src.indexOf('function overlay()');
if (start < 0 || end < 0) throw new Error('layoutLabels not found');
const body = src.slice(start, end);
const clamp = (v, a, z) => Math.min(z, Math.max(a, v));
const layoutLabels = new Function('clamp', body + '\nreturn layoutLabels;')(clamp);

let pass = 0, fail = 0;
const ok = (cond, msg) => { if (cond) { pass++; } else { fail++; console.error('FAIL:', msg); } };

// 构造 8 个挤在同一团中心（模拟截图中肌肉名称堆叠）的锚点。
function makeCluster(n, cx, cy, spread) {
  const items = [];
  for (let i = 0; i < n; i++) {
    const anchor = { x: cx + (Math.sin(i * 12.9) * spread), y: cy + (Math.cos(i * 7.3) * spread) };
    const hw = 60 + (i % 3) * 14, hh = 25;
    items.push({ o: { id: i + 1 }, anchor, w: hw * 2, h: 25, hw, hh });
  }
  return items;
}
const b = { width: 900, height: 700 };
const items = makeCluster(8, 450, 340, 14);
const laid = layoutLabels(items, b);

ok(laid.length === 8, `应保留全部 8 个标签，实际 ${laid.length}`);

// 1) 两两矩形不重叠（留 6px 间隙，与实现一致）。
let overlap = 0;
for (let i = 0; i < laid.length; i++)
  for (let j = i + 1; j < laid.length; j++) {
    const a = laid[i], q = laid[j];
    if (Math.abs(a.x - q.x) < (a.hw + q.hw) / 2 + 5.9 &&
        Math.abs(a.y - q.y) < (a.hh + q.hh) / 2 + 5.9) overlap++;
  }
ok(overlap === 0, `标签两两不得重叠，重叠对数 ${overlap}`);

// 2) 全部在画布安全边界内。
const out = laid.filter(it => it.x < it.hw / 2 || it.x > b.width - it.hw / 2 || it.y < it.hh / 2 || it.y > b.height - it.hh / 2);
ok(out.length === 0, `标签不得越界，越界 ${out.length}`);

// 3) 密集簇中大多数标签被外推，应出现引导线（核心区域不被盖住）。
const leaders = laid.filter(it => it.lead).length;
ok(leaders >= 6, `密集簇应大量使用引导线外推，实际 ${leaders}/8`);

// 4) 引导线起点边缘点必须在标签边缘、且比标签中心更靠近锚点。
let badEdge = 0;
for (const it of laid) {
  if (!it.lead) continue;
  const within = Math.abs(it.edgeY - it.y) <= it.hh / 2 + 0.1 && Math.abs(it.edgeX - it.x) <= it.hw / 2 + 0.1;
  if (!within) badEdge++;
}
ok(badEdge === 0, `引导线边缘点异常 ${badEdge}`);

// 5) 单个标签直接贴锚点、不画引导线。
const single = layoutLabels([{ o: { id: 99 }, anchor: { x: 450, y: 340 }, w: 120, h: 25, hw: 60, hh: 25 }], b);
ok(single.length === 1 && single[0].x === 450 && single[0].y === 340 && !single[0].lead, '单标签应原位显示且无引导线');

// 6) 越界锚点被夹回画布内。
const edge = layoutLabels([{ o: { id: 1 }, anchor: { x: 5, y: 5 }, w: 160, h: 25, hw: 80, hh: 25 }], b);
ok(edge[0].x >= 80 && edge[0].y >= 12.5, '近边界单标签应被夹回安全区');

console.log(`\nlabel layout: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
