// Pure functions shared by the renderer and regression tests. All times are absolute.
export const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
export const frameAt = (seconds, fps) => Math.round(seconds * fps);
export function activeWindow(windows, frame, fps) {
  if (!windows.length || frame < frameAt(windows[0].start, fps)) throw Error('Missing opening state');
  // In a gap keep the preceding COMPLETE state; never fall back to the final scene.
  return windows.findLast(w => frame >= frameAt(w.start, fps));
}
export function anchorProgress(window, anchorId, frame, fps, seconds = 0.4) {
  const a = window.anchors.find(a => a.id === anchorId);
  if (!a) throw Error(`Missing anchor: ${window.id}/${anchorId}`);
  const p = clamp((frame - frameAt(a.time, fps)) / Math.max(1, frameAt(seconds, fps)));
  return 1 - (1 - p) ** 3;
}
export function validateTimeline(t) {
  if (!Number.isFinite(t.fps) || t.fps <= 0 || !Number.isFinite(t.durationSeconds) || t.durationSeconds <= 0) throw Error('Invalid duration/fps');
  if (!t.semanticWindows?.length) throw Error('No semantic windows');
  const ids = new Set();
  let end = 0;
  for (const [i, w] of t.semanticWindows.entries()) {
    if (!w.id || ids.has(w.id)) throw Error('Duplicate/missing window ID');
    ids.add(w.id);
    if (![w.start,w.end,w.holdUntil].every(Number.isFinite) || w.start < end || w.end <= w.start || w.end > t.durationSeconds || w.holdUntil < w.end) throw Error(`Invalid window: ${w.id}`);
    if (i === 0 && w.start !== 0) throw Error('Opening must start at zero');
    if (frameAt(w.end,t.fps) <= frameAt(w.start,t.fps)) throw Error('Sub-frame scene');
    if (w.start > end && t.gapPolicy !== 'hold-previous') throw Error('Gap policy required');
    if (!w.render?.kind || !w.render.title || !w.anchors?.length) throw Error(`Missing render contract: ${w.id}`);
    const anchorIds = new Set();
    for (const a of w.anchors) {
      if (!a.id || anchorIds.has(a.id) || !Number.isFinite(a.time) || !Number.isFinite(a.holdUntil) || a.time < w.start || a.time >= w.end || a.holdUntil > w.holdUntil || a.holdUntil < a.time + 0.6) throw Error(`Invalid anchor: ${w.id}`);
      anchorIds.add(a.id);
    }
    for (const id of w.render.anchorIds || []) if (!anchorIds.has(id)) throw Error(`Unknown render anchor: ${id}`);
    end = w.end;
  }
  if (end < t.durationSeconds && t.gapPolicy !== 'hold-previous') throw Error('Tail gap policy required');
  let cueEnd = 0;
  for (const cue of t.subtitleCues || []) {
    if (![cue.start,cue.end].every(Number.isFinite) || cue.start < cueEnd || cue.end <= cue.start || cue.end > t.durationSeconds || !cue.text) throw Error('Invalid subtitle timing');
    cueEnd = cue.end;
  }
  return t;
}
export const inset = (r, p) => ({x:r.x+p,y:r.y+p,w:r.w-2*p,h:r.h-2*p});
export const expand = (r,p) => inset(r,-p);
export const contains = (a,b) => b.x >= a.x && b.y >= a.y && b.x+b.w <= a.x+a.w && b.y+b.h <= a.y+a.h;
export const overlaps = (a,b) => a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+a.h > b.y;
export function validRect(r) {
  if (!r || ![r.x,r.y,r.w,r.h].every(Number.isFinite) || r.w <= 0 || r.h <= 0) throw Error('Invalid rectangle');
  return r;
}
export function containImage(source, viewport) {
  validRect({x:0,y:0,...source}); validRect(viewport);
  const scale = Math.min(viewport.w/source.w, viewport.h/source.h);
  return {x:viewport.x+(viewport.w-source.w*scale)/2,y:viewport.y+(viewport.h-source.h*scale)/2,w:source.w*scale,h:source.h*scale,scale};
}
export function mapSourceRect(target, source, viewport) {
  validRect(target);
  if (!contains({x:0,y:0,...source},target)) throw Error('Target outside source');
  const image = containImage(source,viewport);
  return {x:image.x+target.x*image.scale,y:image.y+target.y*image.scale,w:target.w*image.scale,h:target.h*image.scale};
}
// Liang-Barsky clipping; conservatively include the stroke in the obstacle bounds.
export function segmentHitsRect(a,b,r) {
  const d=[b.x-a.x,b.y-a.y], p=[-d[0],d[0],-d[1],d[1]], q=[a.x-r.x,r.x+r.w-a.x,a.y-r.y,r.y+r.h-a.y];
  let lo=0, hi=1;
  for(let i=0;i<4;i++) {
    if(p[i]===0) {if(q[i]<0) return false;}
    else {const v=q[i]/p[i]; if(p[i]<0)lo=Math.max(lo,v);else hi=Math.min(hi,v); if(lo>hi)return false;}
  }
  return true;
}
export function annotationBox(target, viewport, avoidRects=[], stroke=5, clearance=12) {
  validRect(target); validRect(viewport);
  const gap=Math.max(clearance,stroke*1.5), box=expand(target,gap+stroke/2);
  if(!contains(viewport,expand(box,stroke/2))) throw Error('No annotation clearance: reframe or use an external label');
  const {x,y,w,h}=box;
  const segments=[[{x,y},{x:x+w,y}],[{x:x+w,y},{x:x+w,y:y+h}],[{x:x+w,y:y+h},{x,y:y+h}],[{x,y:y+h},{x,y}]];
  for(const r of [target,...avoidRects]) for(const [a,b] of segments) if(segmentHitsRect(a,b,expand(r,stroke/2))) throw Error('Annotation crosses content');
  return box;
}
export const pathLength = points => points.slice(1).reduce((n,p,i)=>n+Math.hypot(p.x-points[i].x,p.y-points[i].y),0);
export function arrowRoute(source,target,obstacles=[],stroke=6) {
  validRect(source); validRect(target);
  // Keep head tips outside the node. Prefer a straight common axis, then one elbow.
  let a,b;
  const gap=stroke*2;
  if(target.y >= source.y+source.h) {a={x:source.x+source.w/2,y:source.y+source.h+gap};b={x:target.x+target.w/2,y:target.y-gap};}
  else if(source.y >= target.y+target.h) {a={x:source.x+source.w/2,y:source.y-gap};b={x:target.x+target.w/2,y:target.y+target.h+gap};}
  else if(target.x >= source.x+source.w) {a={x:source.x+source.w+gap,y:source.y+source.h/2};b={x:target.x-gap,y:target.y+target.h/2};}
  else if(source.x >= target.x+target.w) {a={x:source.x-gap,y:source.y+source.h/2};b={x:target.x+target.w+gap,y:target.y+target.h/2};}
  else throw Error('Overlapping arrow nodes');
  const candidates=a.x===b.x || a.y===b.y ? [[a,b]] : [[a,{x:a.x,y:b.y},b],[a,{x:b.x,y:a.y},b]];
  for(const points of candidates) {
    // The clearance also covers the arrowhead's width, not only the center line.
    const blocked=[source,target,...obstacles].some(r=>points.slice(1).some((p,i)=>segmentHitsRect(points[i],p,expand(r,stroke))));
    if(!blocked && pathLength(points)>stroke*4)return points;
  }
  throw Error('No clear arrow route: rearrange nodes');
}
export function visiblePath(points,progress,stroke=6) {
  const length=pathLength(points), visible=length*clamp(progress);
  if(visible<=stroke*2)return null;
  let remaining=visible;
  const result=[points[0]];
  for(let i=1;i<points.length;i++) {
    const a=points[i-1],b=points[i],n=Math.hypot(b.x-a.x,b.y-a.y);
    if(remaining>=n){result.push(b);remaining-=n;}
    else {result.push({x:a.x+(b.x-a.x)*remaining/n,y:a.y+(b.y-a.y)*remaining/n});break;}
  }
  return result;
}
export function wrapText(text,measure,width,maxLines=2) {
  // Prefer semantic/punctuation boundaries and balanced lines over a one-character tail.
  if(maxLines===2 && !text.includes('\n') && measure(text)>width) {
    const boundaries=new Intl.Segmenter('zh',{granularity:'word'}).segment(text);
    const candidates=[...boundaries].map(s=>s.index+s.segment.length).filter(i=>i<text.length).map(i=>{
      const left=text.slice(0,i).trim(),right=text.slice(i).trim();
      const a=measure(left),b=measure(right);
      return {left,right,a,b,score:Math.abs(a-b)+(/[，。！？；：、]$/.test(left)?0:width*0.25)};
    }).filter(c=>c.a<=width && c.b<=width && c.a>0 && c.b>0 && !/^[，。！？、；：）】》]/.test(c.right));
    candidates.sort((a,b)=>a.score-b.score);
    if(candidates.length)return [candidates[0].left,candidates[0].right];
  }
  // Keep Latin brands/acronyms and decimal numbers intact; Chinese can wrap by glyph.
  const tokens=text.match(/[A-Za-z0-9]+(?:[._+-][A-Za-z0-9]+)*|\r?\n|\s+|[^\s]/gu)||[];
  const lines=[];let line='';
  for(const token of tokens) {
    if(token.includes('\n')) {if(line.trim())lines.push(line.trim());line='';continue;}
    if(measure(token.trim())>width)throw Error('Unbreakable token exceeds width');
    if(measure(line+token)<=width)line+=token;
    else {
      if(/^[，。！？、；：,.!?;:）】》]/u.test(token)) {
        const chars=Array.from(line.trimEnd()), last=chars.pop();
        if(!last)throw Error('Punctuation cannot fit');
        lines.push(chars.join(''));line=last+token;
      } else {lines.push(line.trim());line=token.trimStart();}
    }
  }
  if(line.trim())lines.push(line.trim());
  if(lines.length>maxLines || lines.some(l=>!l || measure(l)>width)) throw Error('Text overflow: split the semantic cue or re-layout');
  return lines;
}
