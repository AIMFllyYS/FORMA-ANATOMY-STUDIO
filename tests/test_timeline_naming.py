"""Browser-fixture checks for the nomenclature layer + timeline primitives.

SYNTHETIC GRAPHICS NOT ANATOMY: the GLB fixture is a sphere-like mesh whose node
names (Left humerus etc.) exist only to exercise name->identity resolution.
No anatomical shape is asserted or shipped.
"""
from pathlib import Path
import sys, os
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture import glb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests' / '_runtime'
OUT.mkdir(exist_ok=True)
CHROME = os.environ.get('CHROMIUM_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')

fails = []
def check(name, value):
    print(('OK  ' if value else 'FAIL'), name, flush=True)
    if not value:
        fails.append(name)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True,
        args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1536, 'height': 960})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('about:blank#no-auto')
    page.set_content((ROOT / 'dist' / 'forma_anatomy_studio.html').read_text(encoding='utf-8'), wait_until='load')
    page.wait_for_function('window.__studio !== undefined')
    page.route('**/systems/*.glb', lambda route: route.fulfill(status=200, content_type='model/gltf-binary', body=glb(),
             headers={'Access-Control-Allow-Origin': '*'}))
    page.locator('[data-action="load-skeleton"]').filter(visible=True).first.click()
    page.wait_for_function('__studio.renderer.objects.length===9')
    page.wait_for_timeout(200)

    # ---- Nomenclature layer ----
    check('nomenclature data loaded', page.evaluate('!!window.FormaNomenclature && FormaNomenclature.loaded'))
    check('curriculum has wrist', page.evaluate('!!FormaCurriculum.lesson("wrist") && FormaCurriculum.lesson("wrist").complete'))
    check('other joints marked incomplete', page.evaluate(
        '["shoulder","elbow","knee"].every(id=>FormaCurriculum.lesson(id)&&!FormaCurriculum.lesson(id).complete)'))
    check('identity resolves for known id', page.evaluate('''()=>{
      // nodeIndex 0 in skeletal is the corpus incus; use the byName fallback
      // with an index that has no byNode mapping for this synthetic object.
      const ident=FormaNomenclature.identity({category:'skeletal',nodeIndex:123456,sourceName:'Humerus',name:'Humerus'});
      return ident && ident.id==='humerus' && ident.la==='Humerus' && ident.zh==='肱骨';
    }'''))
    check('identity null for unmatched', page.evaluate(
        "FormaNomenclature.identity({category:'skeletal',nodeIndex:99999,sourceName:'ZZZ NODE',name:'ZZZ'})===null"))
    check('fixture humerus gets zh', page.evaluate(
        "FormaKnowledge.names(__studio.object(0)).matched && FormaKnowledge.names(__studio.object(0)).zh.includes('肱骨')"))
    page.evaluate('__studio.select(__studio.object(0))')
    page.wait_for_timeout(120)
    check('detail heading zh', '肱骨' in page.locator('#learn-panel h2').first.inner_text())
    check('trust badge present', page.locator('#learn-panel .nom-reviewed, #learn-panel .nom-pending, #learn-panel .nom-unmapped').count() >= 1)

    # Latin + pinyin + chinese search through the merged names() pipeline.
    page.locator('#search').fill('肱骨'); page.wait_for_timeout(200)
    check('chinese search', page.locator('#catalog .mesh-row').count() >= 2)
    page.locator('#search').fill('gong'); page.wait_for_timeout(200)
    check('pinyin substring search', page.locator('#catalog .mesh-row').count() >= 1)
    page.locator('#search').fill('humerus'); page.wait_for_timeout(200)
    check('english search', page.locator('#catalog .mesh-row').count() >= 2)
    page.locator('#search').fill(''); page.wait_for_timeout(150)

    # ---- Timeline primitives (synthetic geometry) ----
    check('timeline module present', page.evaluate('!!window.FormaTimeline && typeof __studio.playAssembly==="function"'))
    seg = page.evaluate('''()=>{
      const r=__studio.renderer, o=r.objects[0];
      // Offset is measured from an explicit center distinct from object center,
      // otherwise a centered fixture object would have a zero assembly vector.
      r.explodeCenter=[0,-50,0];
      const a=FormaTimeline.assembly(r,[o],{from:0.5,to:0,duration:1});
      a.apply(0); const start=r.timelineOffsets.get(o.id);
      a.apply(1); const end=r.timelineOffsets.get(o.id);
      const m=FormaTimeline.rigidMotion(r,{ids:new Set([o.id]),pointA:[0,0,0],pointB:[1,0,0],startAngle:0,endAngle:90,duration:1});
      m.apply(0.5); const mm=r.timelineMatrixFor(o); const moving=!!mm&&mm.length===16;
      const other=r.timelineMatrixFor(r.objects[1]);
      r.timelineMatrixFor=()=>null;r.timelineOffsets.clear();r.explodeCenter=null;
      return {startIsOffset:Array.isArray(start)&&start.some(v=>v!==0), endZero:Array.isArray(end)&&end.every(v=>v===0), moving, otherNull:other===null};
    }''')
    check('assembly offsets 0.5->0', seg['startIsOffset'] and seg['endZero'])
    check('rigid motion matrix channel', seg['moving'] and seg['otherNull'])

    axis_err = page.evaluate('''()=>{
      try{__studio.solveAxis({anchorIds:['definitely_missing_id_xyz'],axisVector:[1,0,0]});return null;}
      catch(e){return e.message;}
    }''')
    check('axis rejects missing anchors', isinstance(axis_err, str) and '锚点' in axis_err)

    # Bind synthetic objects 0/1 (Left/Right humerus in the fixture) to the
    # real humerus record for id-based APIs, matching both L and R sides.
    page.evaluate('''()=>{
      const mk=s=>({rec:FormaNomenclature.records.humerus, assignment:{side:s,status:'reviewed'}, status:'reviewed'});
      // override any cached null resolution from earlier identity() calls
      FormaNomenclature.reset(__studio.object(0));
      FormaNomenclature.reset(__studio.object(4));
      __studio.object(0)._nomenclature=mk('L');
      __studio.object(4)._nomenclature=mk('R');
    }''')
    check('axis solver from bounds', page.evaluate('''()=>{
      const ax=__studio.solveAxis({anchorIds:['humerus'],axisVector:[1,0,0]});
      return ax.pointA.length===3 && ax.pointB.length===3 && !!ax.name;
    }'''))
    hlres = page.evaluate('''async ()=>{
      let out;
      try{out=await __studio.executeTool('set_highlight',{ids:['humerus'],state:'contraction'});}
      catch(e){out={error:e.message};}
      return {out, st0:__studio.renderer.highlightState.get(0)};
    }''')
    print('HLRES', hlres)
    check('contraction highlight', hlres['st0'] == 'contraction')

    asm = page.evaluate('''async ()=>{
      const out=__studio.playAssembly([{system:'skeletal',ids:['humerus'],zh:'TEST_NOT_ANATOMY'}],{stepDuration:0.2});
      __studio.timeline.renderAt(999); __studio.timeline._finish();
      await new Promise(r=>setTimeout(r,20));
      return out.played;
    }''')
    check('playAssembly gathers objects', asm >= 1)

    motion_err = page.evaluate('''async ()=>{
      try{await __studio.executeTool('play_joint_motion',{joint:'wrist',motion:'flexion_extension'});return null;}
      catch(e){return e.message;}
    }''')
    check('motion requires loaded moving group', isinstance(motion_err, str) and ('骨组' in motion_err or '加载' in motion_err))

    page.evaluate('__studio.executeTool("stop_animation",{})')
    check('stop clears channels', page.evaluate('__studio.renderer.highlightState.size===0 && __studio.renderer.timelineOffsets.size===0'))

    budget = page.evaluate('''()=>{
      const r=__studio.renderer,tl=new FormaTimeline.Timeline(r);let total=-1;
      tl.play([FormaTimeline.assembly(r,[r.objects[0]],{duration:100})],{budgetSeconds:2,instant:true,onfinish(){total=tl.total;}});
      return total;
    }''')
    check('budget clamps total', 0 < budget <= 2.0001)

    instant = page.evaluate('''()=>{
      const r=__studio.renderer,tl=new FormaTimeline.Timeline(r);let fired=false;
      tl.play([FormaTimeline.assembly(r,[r.objects[0]],{duration:1})],{instant:true,onfinish(){fired=true;}});
      return fired && !tl.playing;
    }''')
    check('instant path finishes', bool(instant))

    tax = page.evaluate('()=>__studio.executeTool("list_taxonomy",{})')
    check('list_taxonomy rows', tax['objects'] == 9 and len(tax['taxonomy']) >= 1)
    lesson = page.evaluate('()=>__studio.executeTool("get_lesson",{joint:"wrist"})')
    check('get_lesson wrist', len(lesson['assembly']) == 7 and len(lesson['motions']) == 2)
    check('get_lesson missing systems honest', 'muscles' in lesson['missingSystems'] and lesson['calibrated'] is False)

    check('no pageerror', errors == [])
    if errors:
        print('ERRORS', errors)
    page.screenshot(path=str(OUT / 'timeline_naming_NOT_ANATOMY.png'))
    browser.close()

print('FAILED' if fails else 'ALL PASSED', fails)
sys.exit(1 if fails else 0)
