import React from 'react';
import {anchorProgress} from './contracts.mjs';
import {Panel,Text,DocumentIcon,EvidencePanel,SafeArrow,TOKENS} from './components.jsx';
export const KINDS=['transfer','fields','evidence','stacked','flow'];
export function Scene({window:w,frame,fps,font}) {
  const d=w.render,progress=i=>anchorProgress(w,d.anchorIds[i],frame,fps),white=d.dark?'#FFF':TOKENS.ink;
  if(d.kind==='transfer') {
    const p=progress(0);
    return <>
      <Panel rect={{x:60,y:530,w:800,h:340}} dark>
        <Text text={p>=1?'文件已收到':'工作区'} x={40} y={38} w={720} size={48} color="#FFF" font={font}/>
        <div style={{position:'absolute',left:40,right:40,top:144,height:130,border:'2px dashed #7593AD',borderRadius:18}}/>
      </Panel>
      {d.files.map((name,i)=><Panel key={name} rect={{x:0,y:50+i*126,w:800,h:110}}><DocumentIcon x={20} y={16}/><Text text={name} x={116} y={26} w={650} size={40} lines={1} font={font}/></Panel>)}
      {p>0&&p<1&&d.files.map((_,i)=>{
        const startY=80+i*126,vertical=Math.min(1,p/0.7),horizontal=Math.max(0,(p-0.7)/0.3);
        return <DocumentIcon key={i} x={862-horizontal*(390-i*42)} y={startY+(730-startY)*vertical} color="#6DE4C7" scale={0.65}/>;
      })}
      {p>=1&&<Text text={`${d.files.length} 份材料，准备就绪`} x={160} y={706} w={640} size={40} color="#6DE4C7" align="center" font={font}/>}
    </>;
  }
  if(d.kind==='fields') {
    const p=progress(0);
    return <>
      {d.fields.map(([label,value],i)=><Panel key={label} rect={{x:0,y:36+i*180,w:920,h:144}}>
        <Text text={label} x={32} y={42} w={170} size={40} color={TOKENS.teal} font={font}/>
        <Text text={value} x={230} y={38} w={630} size={48} lines={1} font={font}/>
        <div style={{position:'absolute',left:32,top:120,height:6,width:850*p,background:TOKENS.blue,borderRadius:3}}/>
      </Panel>)}
      <Panel rect={{x:0,y:700,w:920,h:210}} dark>
        <DocumentIcon x={32} y={48} color="#6DE4C7"/>
        <Text text={p>=1?d.result:'等待组合'} x={130} y={50} w={746} size={42} color="#FFF" font={font}/>
      </Panel>
    </>;
  }
  if(d.kind==='evidence') {
    const i=d.anchorIds.findLastIndex(id=>anchorProgress(w,id,frame,fps)>0),target=i>=0?d.targets[i]:undefined;
    return <>
      <EvidencePanel asset={d.asset} source={d.source} viewport={{x:0,y:70,w:920,h:650}} target={target} avoidRects={d.avoidRects||[]} progress={i>=0?progress(i):0}/>
      <Text text={i>=0?(d.captions?.[i]||['先核对结果','再看处理范围'][i]||'核对结果'):'完整记录'} x={0} y={800} w={920} size={48} color={TOKENS.teal} align="center" font={font}/>
    </>;
  }
  if(d.kind==='stacked')return <>
    {d.assets.map((asset,i)=><EvidencePanel key={asset} asset={asset} source={d.source} viewport={{x:0,y:i*514,w:920,h:480}} target={d.targets[i]} progress={progress(i)}/>)}
  </>;
  if(d.kind==='flow') {
    const nodes=d.nodes.map((text,i)=>({text,x:120,y:20+i*350,w:680,h:200}));
    return <>
      {nodes.map((r,i)=><Panel key={r.text} rect={r} dark={d.dark}>
        <Text text={r.text} x={32} y={62} w={616} size={52} color={i===0||progress(i-1)>=1?'#6DE4C7':white} align="center" font={font}/>
      </Panel>)}
      {nodes.slice(1).map((r,i)=><SafeArrow key={i} source={nodes[i]} target={r} progress={progress(i)} color="#6DE4C7"/>)}
    </>;
  }
  throw Error(`Unsupported visual grammar ${d.kind}: author a scene; do not fall back to a generic card`);
}
