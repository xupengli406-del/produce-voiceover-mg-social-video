import {test} from 'node:test';
import assert from 'node:assert/strict';
import {activeWindow,anchorProgress,frameAt,mapSourceRect,annotationBox,arrowRoute,visiblePath,segmentHitsRect,wrapText,validateTimeline} from '../src/contracts.mjs';
import {fixture} from '../src/fixture.mjs';
test('all 960 frame states exist; gaps hold previous and boundaries switch once',()=>{
  const t=validateTimeline(fixture);let prev=-1;
  for(let f=0;f<960;f++) {const w=activeWindow(t.semanticWindows,f,t.fps),i=t.semanticWindows.indexOf(w);assert.ok(i>=prev);prev=i;}
  assert.equal(activeWindow(t.semanticWindows,515,30).id,'evidence');
  assert.equal(activeWindow(t.semanticWindows,522,30).id,'stacked');
  assert.equal(frameAt(3.2,30),96);
});
test('anchors use global time and do not restart in held windows',()=>{
  const w=fixture.semanticWindows[2],a=w.anchors[0];
  assert.equal(anchorProgress(w,a.id,frameAt(a.time,30)-1,30),0);
  assert.equal(anchorProgress(w,a.id,frameAt(a.time+1,30),30),1);
  assert.equal(anchorProgress(w,a.id,520,30),1);
  assert.throws(()=>anchorProgress(w,'missing',400,30));
});
test('reject malformed timings instead of guessing',()=>{
  for(const mutate of [t=>t.semanticWindows[0].start=1,t=>t.semanticWindows[1].start=2,t=>t.semanticWindows[0].anchors[0].time=99,t=>t.semanticWindows[0].render.anchorIds=['absent'],t=>t.semanticWindows[0].end=0.001]){
    const t=structuredClone(fixture);mutate(t);assert.throws(()=>validateTimeline(t));
  }
});
test('source annotations follow contain letterboxing and target size',()=>{
  const src={w:1000,h:500},vp={x:80,y:400,w:920,h:800};
  assert.deepEqual(mapSourceRect({x:0,y:0,w:1000,h:500},src,vp),{x:80,y:570,w:920,h:460});
  const a=annotationBox({x:150,y:600,w:250,h:50},vp),b=annotationBox({x:150,y:600,w:600,h:100},vp);
  assert.ok(b.w>a.w && b.h>a.h);assert.throws(()=>mapSourceRect({x:990,y:0,w:40,h:50},src,vp));
});
test('marks fail closed at edges and adjacent text; no ellipse cuts long text',()=>{
  const vp={x:0,y:0,w:1080,h:1920},r={x:100,y:400,w:600,h:80};
  assert.throws(()=>annotationBox({x:0,y:0,w:200,h:100},vp));
  assert.throws(()=>annotationBox(r,vp,[{x:90,y:380,w:640,h:20}]));
  const box=annotationBox(r,vp);assert.ok(box.x<r.x && box.y<r.y && box.w>r.w);
});
test('arrows avoid obstacles and hide zero/near-zero cap dots',()=>{
  const s={x:200,y:400,w:680,h:160},t={x:200,y:720,w:680,h:160};
  const p=arrowRoute(s,t);assert.equal(p[0].x,p[1].x);
  assert.equal(visiblePath(p,0),null);assert.equal(visiblePath(p,0.01),null);
  assert.ok(visiblePath(p,1));assert.throws(()=>arrowRoute(s,t,[{x:400,y:600,w:200,h:60}]));
  assert.equal(segmentHitsRect({x:0,y:0},{x:10,y:10},{x:4,y:4,w:2,h:2}),true);
});
test('Chinese captions wrap without splitting WorkBuddy and reject a third line',()=>{
  const m=s=>Array.from(s).reduce((n,c)=>n+(/[A-Za-z0-9]/.test(c)?6:12),0);
  const lines=wrapText('用 WorkBuddy 整理文件，然后查看结果。',m,210,2);
  assert.ok(lines.join('').includes('WorkBuddy'));assert.ok(lines.length<=2);
  assert.throws(()=>wrapText('完整句子'.repeat(50),m,210,2));
  assert.throws(()=>wrapText('VeryLongUnbreakableBrandName',m,20,2));
  const balanced=wrapText('这次改了哪些文件，哪些没有改，都要看清。',m,230,2);
  assert.ok(balanced[1].length>3);
  assert.ok(!balanced[0].endsWith('看'));
});
