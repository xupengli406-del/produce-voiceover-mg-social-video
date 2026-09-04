import React,{useLayoutEffect} from 'react';
import {Img,staticFile} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {annotationBox,arrowRoute,visiblePath,containImage,mapSourceRect,wrapText,overlaps,contains} from './contracts.mjs';

export const TOKENS={font:'PingFang SC',ink:'#15283E',blue:'#146BFF',teal:'#008F7E',red:'#E95149',paper:'#F6F3EC',stroke:5};
export const REGIONS={title:{x:80,y:130,w:920,h:230},main:{x:80,y:400,w:920,h:1000},subtitle:{x:80,y:1540,w:920,h:220}};
export const position=r=>({position:'absolute',left:r.x,top:r.y,width:r.w,height:r.h});
export function Text({text,x=0,y=0,w,size=44,weight=600,color=TOKENS.ink,lines=2,align='left',font=TOKENS.font}) {
  const measured=s=>measureText({text:s,fontFamily:font,fontSize:size,fontWeight:weight,validateFontIsLoaded:true}).width;
  const wrapped=wrapText(text,measured,w,lines);
  return <div data-qa-text style={{...position({x,y,w,h:wrapped.length*size*1.35}),fontFamily:font,fontSize:size,fontWeight:weight,color,lineHeight:1.35,textAlign:align,whiteSpace:'pre'}}>{wrapped.join('\n')}</div>;
}
export function DocumentIcon({x=0,y=0,color=TOKENS.blue,scale=1}) {
  return <svg style={{position:'absolute',left:x,top:y,width:64*scale,height:78*scale}} viewBox="0 0 64 78" fill="none" aria-hidden="true"><path d="M10 3H42L59 21V73H10Z M42 3V22H59 M21 37H47 M21 49H47 M21 61H39" stroke={color} strokeWidth="4" strokeLinejoin="round"/></svg>;
}
export function Panel({rect,children,dark=false}) {
  return <div style={{...position(rect),background:dark?'#173A5B':'#FFF',border:'2px solid '+(dark?'#385774':'#DFE6ED'),borderRadius:26,boxSizing:'border-box'}}>{children}</div>;
}
export function SafeAnnotation({target,viewport,avoidRects=[],progress,color=TOKENS.red}) {
  const stroke=TOKENS.stroke,box=annotationBox(target,viewport,avoidRects,stroke,12),length=2*(box.w+box.h);
  if(length*progress<=2*stroke)return null;
  return <svg data-qa-mark style={{position:'absolute',inset:0,width:'100%',height:'100%',pointerEvents:'none',overflow:'visible'}}>
    <rect x={box.x} y={box.y} width={box.w} height={box.h} fill="none" stroke={color} strokeWidth={stroke} strokeLinejoin="round" pathLength="1" strokeDasharray="1" strokeDashoffset={1-progress}/>
  </svg>;
}
export function SafeArrow({source,target,obstacles=[],progress,color=TOKENS.teal}) {
  const path=arrowRoute(source,target,obstacles),shown=visiblePath(path,progress);
  if(!shown)return null;
  const end=shown.at(-1),prev=shown.at(-2),angle=Math.atan2(end.y-prev.y,end.x-prev.x);
  const tip=(offset)=>`${end.x-14*Math.cos(angle+offset)},${end.y-14*Math.sin(angle+offset)}`;
  return <svg data-qa-mark style={{position:'absolute',inset:0,width:'100%',height:'100%',pointerEvents:'none'}}>
    <polyline points={shown.map(p=>`${p.x},${p.y}`).join(' ')} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>
    {progress>=1 && <polyline points={`${tip(-0.5)} ${end.x},${end.y} ${tip(0.5)}`} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>}
  </svg>;
}
export function EvidencePanel({asset,source,viewport,target,avoidRects=[],progress=0}) {
  const image=containImage(source,viewport),mapped=target&&mapSourceRect(target,source,viewport);
  return <>
    <div style={{...position(viewport),border:'2px solid #DFE6ED',borderRadius:26,background:'#fff',boxSizing:'border-box'}}/>
    <Img src={staticFile(asset)} onLoad={e=>{if(e.currentTarget.naturalWidth!==source.w||e.currentTarget.naturalHeight!==source.h)throw Error('Source dimensions differ from annotation coordinates');}} style={{...position(image),objectFit:'contain'}}/>
    {mapped && <SafeAnnotation target={mapped} viewport={viewport} avoidRects={avoidRects.map(r=>mapSourceRect(r,source,viewport))} progress={progress}/>}
  </>;
}
export function LayoutAudit({frame,windowId}) {
  useLayoutEffect(()=>{
    const els=[...document.querySelectorAll('[data-qa-region]')];
    const boxes=els.map(el=>({name:el.dataset.qaRegion,rect:el.getBoundingClientRect()}));
    const box=r=>({x:r.left,y:r.top,w:r.width,h:r.height});
    for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++)if(overlaps(box(boxes[i].rect),box(boxes[j].rect)))throw Error(`Layout collision: ${boxes[i].name}/${boxes[j].name}`);
    for(const el of document.querySelectorAll('[data-qa-text]')) {
      const region=el.closest('[data-qa-region]');
      if(region && !contains(box(region.getBoundingClientRect()),box(el.getBoundingClientRect())))throw Error('Text leaves its protected region');
      if(el.scrollWidth>el.clientWidth+1 || el.scrollHeight>el.clientHeight+1)throw Error('Rendered text overflow');
    }
    // Failures throw into the render report; no per-frame logs or painted debug text.
  },[frame,windowId]);
  return null;
}
