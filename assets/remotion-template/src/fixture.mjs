// Synthetic visual regression fixture, NOT a voiceover alignment or product evidence.
const window = (id,start,end,title,kind,times,data={},dark=false) => ({
  id,start,end,holdUntil:end,coverageStatus:'covered',
  anchors:times.map((time,i)=>({id:`${id}-${i}`,time,phrase:'合成测试锚点',holdUntil:end})),
  render:{kind,title,dark,anchorIds:times.map((_,i)=>`${id}-${i}`),...data}
});
export const fixture={
  schemaVersion:3,fps:30,durationSeconds:32,gapPolicy:'hold-previous',
  canvas:{width:1080,height:1920},timingSource:{method:'synthetic-diagnostic',audio:''},
  semanticWindows:[
    window('transfer',0,5.5,'把文件交给它','transfer',[1.2],{files:['季度复盘.docx','会议录音.m4a','销售数据.xlsx']},true),
    window('fields',5.5,11,'名字，从混乱到有序','fields',[7.4],{fields:[['日期','2026-09-04'],['主题','季度复盘'],['类型','文档']],result:'2026-09-04_季度复盘_文档'}),
    window('evidence',11,17,'改了哪些，一眼看清','evidence',[12.2,14.5],{asset:'fixture-evidence.svg',source:{w:920,h:480},targets:[{x:56,y:130,w:337,h:53},{x:56,y:332,w:578,h:48}]}),
    window('stacked',17.4,22.5,'两张图，都要看得清','stacked',[18.5,20],{assets:['fixture-evidence.svg','fixture-result.svg'],source:{w:920,h:480},targets:[{x:56,y:130,w:337,h:53},{x:56,y:130,w:608,h:53}]}),
    window('flow',22.5,28,'每一步，都有去有回','flow',[23.5,25],{nodes:['收到任务','按计划处理','返回结果']},true),
    window('result',28,32,'结果留下，方便核对','evidence',[28.8],{asset:'fixture-result.svg',source:{w:920,h:480},targets:[{x:56,y:130,w:608,h:53}]})
  ],
  subtitleCues:[
    {start:0,end:5.5,text:'先把要处理的文件交给它。'},
    {start:5.5,end:11,text:'日期、主题、类型，组合成统一的名字。'},
    {start:11,end:17.4,text:'这次改了哪些文件，哪些没有改，都要看清。'},
    {start:17.4,end:22.5,text:'两张图上下放，给每一张留够空间。'},
    {start:22.5,end:28,text:'收到任务，按计划处理，再把结果交回来。'},
    {start:28,end:32,text:'让观众来得及看清，再进入下一步。'}
  ]
};
