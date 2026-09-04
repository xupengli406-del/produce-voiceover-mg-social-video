import React,{useEffect,useState} from 'react';
import {AbsoluteFill,Audio,Composition,continueRender,delayRender,cancelRender,getInputProps,staticFile,useCurrentFrame} from 'remotion';
import {activeWindow,validateTimeline} from './contracts.mjs';
import {Text,REGIONS,position,LayoutAudit,TOKENS} from './components.jsx';
import {Scene} from './scenes.jsx';
import {fixture} from './fixture.mjs';

function Video({timeline,diagnostic=false,fontFamily='PingFang SC',injectOverflow=false}) {
  const frame=useCurrentFrame(),w=activeWindow(timeline.semanticWindows,frame,timeline.fps);
  const [ready,setReady]=useState(false),[handle]=useState(()=>delayRender('Load actual production font'));
  useEffect(()=>{Promise.all([400,600,700].map(weight=>document.fonts.load(`${weight} 48px "${fontFamily}"`))).then(()=>document.fonts.ready).then(()=>{setReady(true);continueRender(handle);}).catch(cancelRender);},[handle,fontFamily]);
  if(!ready)return null;
  const cue=timeline.subtitleCues?.find(c=>frame>=Math.round(c.start*timeline.fps)&&frame<Math.round(c.end*timeline.fps));
  return <AbsoluteFill style={{background:w.render.dark?'#0B233D':TOKENS.paper,fontFamily}}>
    {timeline.timingSource.audio && <Audio src={staticFile(timeline.timingSource.audio)}/>}
    <div data-qa-region="title" style={position(REGIONS.title)}>
      <Text text={w.render.title} w={920} size={76} weight={700} color={w.render.dark?'#FFF':TOKENS.ink} font={fontFamily}/>
    </div>
    <div data-qa-region="main" style={position(REGIONS.main)}>
      <Scene window={w} frame={frame} fps={timeline.fps} font={fontFamily}/>
    </div>
    <div data-qa-region="subtitle" style={{...position(REGIONS.subtitle),background:w.render.dark?'#183A59':'#FFF',borderRadius:24}}>
      {cue&&<Text text={injectOverflow?'完整语义不能被缩成小字'.repeat(40):cue.text} x={32} y={40} w={856} size={46} color={w.render.dark?'#FFF':TOKENS.ink} align="center" font={fontFamily}/>}
    </div>
    {diagnostic&&<div style={{position:'absolute',top:72,right:80,fontSize:26,color:w.render.dark?'#96AFC6':'#607487'}}>示意</div>}
    <LayoutAudit frame={frame} windowId={w.id} diagnostic={diagnostic}/>
  </AbsoluteFill>;
}
export function Root() {
  const input=getInputProps(),diagnostic=!input.timeline;
  const timeline=validateTimeline(input.timeline||fixture);
  if(!diagnostic && (!input.sourceSha256 || !timeline.timingSource?.audio))throw Error('Production requires prepared timeline and final audio');
  return <Composition id={diagnostic?'MotionLab':'VoiceoverMG'} component={Video} width={1080} height={1920} fps={timeline.fps} durationInFrames={Math.ceil(timeline.durationSeconds*timeline.fps)} defaultProps={{timeline,diagnostic,fontFamily:input.fontFamily||'PingFang SC',injectOverflow:input.injectOverflow||false}}/>;
}
