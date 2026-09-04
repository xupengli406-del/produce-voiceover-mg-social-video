#!/usr/bin/env python3
"""Validate and stage a real final-audio timeline. Never infer timings or approve QA."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = {'transfer', 'fields', 'evidence', 'stacked', 'flow'}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare(project: Path) -> Path:
    timeline_path = project / 'work/timeline.json'
    visual = project / 'work/visual/remotion'
    if not (visual / 'package.json').is_file():
        raise ValueError('Initialize a Remotion project first; existing projects require an explicit migration')
    for script, args in (
        ('validate_narrative_plan.py', [project / 'brief.md', timeline_path]),
        ('validate_av_timeline.py', [timeline_path]),
        ('validate_visual_plan.py', [project / 'brief.md', timeline_path, '--stage', 'assets']),
    ):
        subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *map(str, args)], cwd=project, check=True)
    data = json.loads(timeline_path.read_text(encoding='utf-8'))
    if data.get('canvas') != {'width':1080,'height':1920}:
        raise ValueError('Current measured layout supports 1080x1920 only; author and test other aspect ratios separately')
    if data['timingSource'].get('method') == 'synthetic-diagnostic':
        raise ValueError('Diagnostic timing is not a production audio alignment')
    def resolve(raw: str) -> Path:
        if not raw:
            raise ValueError('Missing input file')
        p = Path(raw)
        return p if p.is_absolute() else project / p
    raw_audio = resolve(data['timingSource'].get('audio',''))
    if sha(raw_audio) != data['timingSource'].get('audioSha256'):
        raise ValueError('Final audio hash changed: rebuild alignment')
    staged = visual / 'public/inputs'
    staged.mkdir(parents=True,exist_ok=True)
    staged_files = {}
    def stage(p: Path) -> str:
        digest = sha(p)
        name = digest + p.suffix.lower()
        dst = staged / name
        if dst.exists() and sha(dst) != digest:
            raise ValueError('Staged input was modified')
        if not dst.exists():
            shutil.copy2(p,dst)
        staged_files['public/inputs/' + name] = digest
        return 'inputs/' + name
    assets = {}
    source_files = [{'path':os.path.relpath(raw_audio,project),'sha256':sha(raw_audio)}]
    for asset in data.get('assets',[]):
        if asset.get('path'):
            p = resolve(asset['path'])
            if sha(p) != asset.get('sha256'):
                raise ValueError('Asset hash mismatch: ' + asset['id'])
            assets[asset['id']] = stage(p)
            source_files.append({'path':os.path.relpath(p,project),'sha256':sha(p)})
    for w in data['semanticWindows']:
        render = w.get('render',{})
        if render.get('kind') not in KINDS:
            raise ValueError('Author and test an explicit render grammar for ' + w['id'])
        ids = {a['id'] for a in w.get('anchors',[])}
        if not render.get('anchorIds') or any(a not in ids for a in render['anchorIds']):
            raise ValueError('Render actions must reference real window anchors: ' + w['id'])
        if render['kind'] in {'evidence','stacked'}:
            refs = render.get('assetIds',[])
            if not refs or any(a not in assets for a in refs):
                raise ValueError('Evidence needs source asset IDs, not arbitrary screenshots')
            render['assets'] = [assets[a] for a in refs]
            render['asset'] = render['assets'][0]
    data['timingSource']['audio'] = stage(raw_audio)
    # This is a compiled derivative, not another editable timing authority.
    props = {'timeline':data,'sourceSha256':sha(timeline_path),'sourceFiles':source_files,'stagedFiles':staged_files,'fontFamily':data.get('renderer',{}).get('fontFamily','PingFang SC')}
    target = visual / 'prepared-props.json'
    target.write_text(json.dumps(props,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return target

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    args = parser.parse_args()
    try:
        print(prepare(args.project.resolve()))
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from exc

if __name__ == '__main__':
    main()
