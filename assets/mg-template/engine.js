(function(){
  const C=document.getElementById("stage");
  const X=C.getContext("2d");
  const W=1080,H=1920;
  const CFG=window.MG_CONFIG;
  const P=CFG.theme;
  let DURATION=CFG.duration;
  let BOUNDS=makeBounds(CFG.scenes.map(function(s){return s.duration;}));
  let GLOBAL=0;

  function makeBounds(durations){
    const values=[0];
    durations.forEach(function(v){values.push(values[values.length-1]+Number(v));});
    DURATION=values[values.length-1];
    return values;
  }
  function clamp(v,a,b){a=a===undefined?0:a;b=b===undefined?1:b;return Math.max(a,Math.min(b,v));}
  function ease(v){v=clamp(v);return 1-Math.pow(1-v,3);}
  function phase(u,start,span){return ease(clamp((u-start)/(span||.1)));}
  function font(n,b){return String(b||700)+" "+String(n)+'px "Noto Sans SC","Microsoft YaHei UI",sans-serif';}
  function rr(x,y,w,h,r,fill,stroke,lw){
    X.beginPath();X.roundRect(x,y,w,h,r);X.fillStyle=fill||P.white;X.fill();
    if(stroke){X.strokeStyle=stroke;X.lineWidth=lw||2;X.stroke();}
  }
  function txt(s,x,y,n,col,b,align,base,max){
    X.font=font(n,b);X.fillStyle=col||P.ink;X.textAlign=align||"left";X.textBaseline=base||"alphabetic";
    if(max){X.fillText(s,x,y,max);}else{X.fillText(s,x,y);}
  }
  function alpha(p,draw){X.save();X.globalAlpha=clamp(p);draw();X.restore();}
  function shadow(x,y,w,h,r,fill,stroke){
    X.save();X.shadowColor="rgba(28,25,20,.14)";X.shadowBlur=24;X.shadowOffsetY=10;
    rr(x,y,w,h,r||24,fill||P.white,stroke,2);X.restore();
  }
  function chip(s,x,y,w,fill,col){
    rr(x,y,w,52,16,fill||P.yellow2);txt(s,x+w/2,y+27,22,col||P.ink,850,"center","middle");
  }
  function paper(){
    X.fillStyle=P.paper;X.fillRect(0,0,W,H);
    X.fillStyle="rgba(40,46,58,.08)";
    for(let y=26;y<H;y+=46){for(let x=26;x<W;x+=46){X.beginPath();X.arc(x,y,1,0,Math.PI*2);X.fill();}}
  }
  function header(tag,index){
    txt(CFG.series,72,68,21,P.gray,850);
    txt(String(index+1).padStart(2,"0")+" / "+String(CFG.scenes.length).padStart(2,"0"),1008,68,21,P.gray,850,"right");
    rr(72,92,936,6,3,"#E3DCCE");
    rr(72,92,936*clamp(GLOBAL/DURATION),6,3,P.blue);
    chip(tag,72,124,280,P.yellow2,P.ink);
  }
  function title(scene){
    txt(scene.title,72,244,61,P.ink,950);
    txt(scene.accent,72,316,61,P.blue,950);
  }
  function check(x,y,col){
    X.beginPath();X.arc(x,y,16,0,Math.PI*2);X.fillStyle=col||P.green;X.fill();
    X.strokeStyle=P.white;X.lineWidth=4;X.lineCap="round";
    X.beginPath();X.moveTo(x-7,y);X.lineTo(x-2,y+6);X.lineTo(x+8,y-8);X.stroke();
  }
  function arrow(x1,y1,x2,y2,p,col){
    p=ease(p);const ex=x1+(x2-x1)*p,ey=y1+(y2-y1)*p;
    X.strokeStyle=col||P.blue;X.lineWidth=6;X.lineCap="round";
    X.beginPath();X.moveTo(x1,y1);X.lineTo(ex,ey);X.stroke();
    if(p>.98){X.beginPath();X.moveTo(x2-16,y2-12);X.lineTo(x2,y2);X.lineTo(x2-16,y2+12);X.stroke();}
  }
  function renderHook(scene,u,index){
    header(scene.tag,index);title(scene);
    alpha(phase(u,.08,.12),function(){
      shadow(72,420,936,410,28,P.white,P.blue);
      chip("一句话结论",112,462,178,P.yellow2,P.ink);
      txt(scene.subtitle,112,596,40,P.ink,950);
      rr(112,676,856,18,9,P.yellow);
    });
    alpha(phase(u,.48,.12),function(){
      shadow(190,920,700,220,28,P.navy);
      txt("输入",240,990,24,P.yellow,900);
      txt("信息 / 概念 / 演示",540,1060,38,P.white,950,"center");
    });
  }
  function renderList(scene,u,index){
    header(scene.tag,index);title(scene);
    const cols=[P.blue,P.green,P.blue,P.coral];
    (scene.items||[]).forEach(function(item,i){
      const p=phase(u,.08+i*.13,.1);
      alpha(.14+.86*p,function(){
        const y=430+i*210;
        shadow(72,y,936,160,24,P.white,cols[i%cols.length]);
        rr(108,y+34,94,94,22,i%2?P.mint:"#E7F0FF");
        txt(String(i+1).padStart(2,"0"),155,y+82,26,P.ink,950,"center","middle");
        txt(item,244,y+82,38,P.ink,950,"left","middle");
        if(p>.9){check(946,y+80,cols[i%cols.length]);}
      });
    });
  }
  function renderWorkflow(scene,u,index){
    header(scene.tag,index);title(scene);
    alpha(phase(u,.03,.08),function(){
      shadow(72,400,936,122,22,P.navy);
      txt("需求",108,462,23,P.yellow,900,"left","middle");
      txt(scene.request,220,462,29,P.white,850,"left","middle",730);
    });
    const steps=scene.steps||[];
    const active=Math.min(steps.length-1,Math.max(0,Math.floor(clamp((u-.16)/.68)*steps.length)));
    steps.forEach(function(item,i){
      const p=phase(u,.16+i*(.62/Math.max(1,steps.length)),.08);
      alpha(.16+.84*p,function(){
        const y=600+i*190;
        shadow(112,y,856,140,22,P.white,i<=active?P.blue:"#D8D0C4");
        chip(String(i+1).padStart(2,"0"),144,y+42,86,i<=active?P.yellow2:"#F0ECE5",P.ink);
        txt(item,266,y+72,34,P.ink,950,"left","middle");
        if(i<active){check(914,y+70,P.green);}
        else if(i===active){rr(884,y+50,60,40,20,P.yellow);txt("执行",914,y+70,18,P.ink,900,"center","middle");}
      });
    });
  }
  function renderCompare(scene,u,index){
    header(scene.tag,index);title(scene);
    [scene.left,scene.right].forEach(function(side,i){
      const p=phase(u,.08+i*.18,.12);
      alpha(.15+.85*p,function(){
        const x=i===0?72:564,col=i===0?P.green:P.blue;
        shadow(x,430,444,610,26,P.white,col);
        chip(side.label,x+40,474,176,i===0?P.mint:"#E7F0FF",P.ink);
        (side.points||[]).forEach(function(point,j){
          rr(x+40,610+j*150,364,110,18,P.white,"#DED7CC");
          txt(point,x+68,666+j*150,27,P.ink,850,"left","middle",280);
          if(p>.8){check(x+365,665+j*150,col);}
        });
      });
    });
    alpha(phase(u,.62,.12),function(){
      shadow(164,1180,752,190,24,P.yellow2,P.ink);
      txt("选择标准",204,1250,25,P.gray,850);
      txt("看当前场景，而不是只数功能",540,1320,34,P.ink,950,"center");
    });
  }
  function renderCta(scene,u,index){
    header(scene.tag,index);title(scene);
    alpha(phase(u,.08,.12),function(){
      shadow(112,450,856,330,30,P.white,P.blue);
      chip("最终结论",156,494,172,P.yellow2,P.ink);
      txt(scene.accent,540,640,42,P.ink,950,"center");
      rr(216,700,648,18,9,P.yellow);
    });
    alpha(phase(u,.46,.12),function(){
      shadow(190,920,700,190,26,P.navy);
      txt(scene.cta,540,1018,38,P.white,950,"center","middle");
    });
    alpha(phase(u,.72,.1),function(){arrow(540,1140,540,1230,1,P.blue);chip("下一步",436,1270,208,P.yellow,P.ink);});
  }
  const RENDERERS={hook:renderHook,list:renderList,workflow:renderWorkflow,compare:renderCompare,cta:renderCta};
  function renderAt(t){
    GLOBAL=clamp(Number(t)||0,0,Math.max(0,DURATION-1/30));paper();
    let idx=BOUNDS.findIndex(function(v,i){return i<BOUNDS.length-1&&GLOBAL>=v&&GLOBAL<BOUNDS[i+1];});
    if(idx<0){idx=CFG.scenes.length-1;}
    const start=BOUNDS[idx],end=BOUNDS[idx+1],u=clamp((GLOBAL-start)/(end-start));
    const scene=CFG.scenes[idx],renderer=RENDERERS[scene.type]||renderHook;
    renderer(scene,u,idx);return true;
  }
  window.renderAt=renderAt;
  window.setTiming=function(bounds,duration){BOUNDS=bounds.map(Number);DURATION=Number(duration);};
  window.setSceneDurations=function(durations){BOUNDS=makeBounds(durations.map(Number));};
  renderAt(0);
})();
