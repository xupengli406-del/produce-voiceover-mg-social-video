import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {bundle} from '@remotion/bundler';
import {openBrowser,selectComposition,renderStill,renderMedia} from '@remotion/renderer';
import {PNG} from 'pngjs';
import {fixture} from '../src/fixture.mjs';
import {frameAt} from '../src/contracts.mjs';

// Usage: node scripts/render.mjs <new-output-dir> [prepared-props.json] [--video]
// Diagnostic mode is deliberately named, synthetic and silent. It cannot approve production.
const args=process.argv.slice(2),out=args.find(a=>!a.startsWith('--'));
if(!out)throw Error('Pass a new output directory');
const output=path.resolve(out),propsPath=args.filter(a=>!a.startsWith('--'))[1];
if(fs.existsSync(output)&&fs.readdirSync(output).length)throw Error('Refusing to overwrite a nonempty output directory');
fs.mkdirSync(output,{recursive:true});
const props=propsPath?JSON.parse(fs.readFileSync(propsPath,'utf8')):{},timeline=props.timeline||fixture,diagnostic=!props.timeline;
if(propsPath) {
  if(!props.timeline || !props.sourceSha256 || !props.sourceFiles?.length || !Object.keys(props.stagedFiles||{}).length)throw Error('Invalid prepared production props');
  const project=path.resolve(path.dirname(propsPath),'../../..');
  const digest=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
  if(digest(path.join(project,'work/timeline.json'))!==props.sourceSha256)throw Error('Stale prepared timeline: prepare again');
  for(const source of props.sourceFiles)if(digest(path.resolve(project,source.path))!==source.sha256)throw Error('Source audio/asset changed: rebuild downstream');
  for(const [name,sha] of Object.entries(props.stagedFiles))if(digest(path.resolve(path.dirname(propsPath),name))!==sha)throw Error('Staged audio/asset changed: prepare again');
}
const report={diagnostic,scope:'component and rendered-frame checks; not a full editorial or listening approval',timelineSha256:crypto.createHash('sha256').update(JSON.stringify(timeline)).digest('hex'),frames:[],events:[],negativeTests:[],fullPlaybackReviewed:false};
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'mg-remotion-bundle-'));
let browser;
const hashes=new Map();
try {
  const serveUrl=await bundle({entryPoint:path.resolve('src/index.jsx'),outDir:temp});
  browser=await openBrowser('chrome',{browserExecutable:process.env.REMOTION_BROWSER_EXECUTABLE});
  const composition=await selectComposition({serveUrl,id:diagnostic?'MotionLab':'VoiceoverMG',inputProps:props,puppeteerInstance:browser});
  const base={serveUrl,composition,inputProps:props,puppeteerInstance:browser,onBrowserLog:()=>{}};
  const max=composition.durationInFrames-1,frames=new Set([0,max]);
  for(const w of timeline.semanticWindows) {
    for(const seconds of [w.start,w.end])for(let d=-3;d<=3;d++)frames.add(Math.max(0,Math.min(max,frameAt(seconds,timeline.fps)+d)));
    for(const a of w.anchors)for(const d of [-1,1,6,14])frames.add(Math.max(0,Math.min(max,frameAt(a.time,timeline.fps)+d)));
  }
  fs.mkdirSync(path.join(output,'frames'));
  for(const frame of [...frames].sort((a,b)=>a-b)) {
    const file=path.join(output,'frames',String(frame).padStart(5,'0')+'.png');
    await renderStill({...base,frame,output:file,imageFormat:'png'});
    const png=PNG.sync.read(fs.readFileSync(file));
    if(png.width!==1080||png.height!==1920)throw Error('Wrong frame dimensions');
    hashes.set(frame,crypto.createHash('sha256').update(png.data).digest('hex'));
    report.frames.push(frame);
  }
  for(const w of timeline.semanticWindows)for(const a of w.anchors) {
    const before=Math.max(0,frameAt(a.time,timeline.fps)-1),after=Math.min(max,frameAt(a.time,timeline.fps)+14);
    const changed=hashes.get(before)!==hashes.get(after);
    if(!changed)throw Error(`Missing rendered action: ${a.id}`);
    report.events.push({anchorId:a.id,before,after,changed});
  }
  const repeated=path.join(output,'determinism.png');
  await renderStill({...base,frame:0,output:repeated,imageFormat:'png'});
  report.deterministic=hashes.get(0)===crypto.createHash('sha256').update(PNG.sync.read(fs.readFileSync(repeated)).data).digest('hex');
  fs.unlinkSync(repeated);
  if(!report.deterministic)throw Error('Nondeterministic frame');
  if(diagnostic) {
    let caught=false;
    try {
      const invalidProps={injectOverflow:true};
      const invalidComposition=await selectComposition({serveUrl,id:'MotionLab',inputProps:invalidProps,puppeteerInstance:browser});
      await renderStill({...base,composition:invalidComposition,inputProps:invalidProps,frame:0,output:path.join(output,'invalid.png')});
    }
    catch(e){if(!/overflow/i.test(String(e)))throw e;caught=true;}
    if(!caught)throw Error('Subtitle overflow was not rejected');
    report.negativeTests.push('three-line/oversize subtitle render rejected');
  }
  if(args.includes('--video')) {
    const file=path.join(output,diagnostic?'画面组件验证片_无旁白.mp4':'成片.mp4');
    await renderMedia({...base,outputLocation:file,codec:'h264',pixelFormat:'yuv420p',crf:18,concurrency:2});
    report.video={file:path.basename(file),sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),frames:composition.durationInFrames};
  }
  report.status='technical-pass';
} catch(e) {report.status='failed';report.error=String(e);process.exitCode=1;}
finally {
  if(browser)await browser.close({silent:true});
  // The path is a newly allocated private compiler scratch directory, never a user input.
  fs.rmSync(temp,{recursive:true,force:true});
  fs.writeFileSync(path.join(output,'render-check.json'),JSON.stringify(report,null,2)+'\n');
}
console.log(JSON.stringify(report,null,2));
