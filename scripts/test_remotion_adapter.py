#!/usr/bin/env python3
"""Adapter behavior tests; semantic acceptance remains the existing validators' job."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import prepare_remotion as adapter

class AdapterTests(unittest.TestCase):
    def test_default_initializer_and_nonempty_guard(self):
        with tempfile.TemporaryDirectory(prefix='mg-init-') as temp:
            p=Path(temp)/'project'
            args=[sys.executable,str(adapter.ROOT/'scripts/init_project.py'),str(p),'--title','示例']
            subprocess.run(args,check=True,capture_output=True)
            self.assertTrue((p/'work/visual/remotion/src/Root.jsx').is_file())
            self.assertFalse((p/'work/visual/mg-template').exists())
            self.assertEqual(json.loads((p/'project-state.json').read_text())['architecture'],'single-main-agent')
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)

    def test_staging_hash_and_anchor_guards(self):
        with tempfile.TemporaryDirectory(prefix='mg-adapter-') as temp:
            p=Path(temp);visual=p/'work/visual/remotion';visual.mkdir(parents=True)
            (visual/'package.json').write_text('{}')
            audio=p/'audio.wav';audio.write_bytes(b'fixture for file hash tests only')
            asset=p/'image.svg';asset.write_text('<svg/>')
            data={'canvas':{'width':1080,'height':1920},'timingSource':{'method':'forced-alignment','audio':'audio.wav','audioSha256':adapter.sha(audio)},'assets':[{'id':'image','path':'image.svg','sha256':adapter.sha(asset)}],'semanticWindows':[{'id':'one','anchors':[{'id':'a'}],'render':{'kind':'evidence','anchorIds':['a'],'assetIds':['image']}}]}
            source=p/'work/timeline.json';source.write_text(json.dumps(data))
            with patch.object(adapter.subprocess,'run') as validators:
                target=adapter.prepare(p)
                self.assertEqual(validators.call_count,3)
            props=json.loads(target.read_text())
            self.assertEqual(props['sourceSha256'],adapter.sha(source))
            self.assertEqual(len(props['sourceFiles']),2)
            self.assertEqual(len(props['stagedFiles']),2)
            for name,digest in props['stagedFiles'].items():
                self.assertEqual(adapter.sha(visual/name),digest)
            self.assertTrue((visual/'public'/props['timeline']['timingSource']['audio']).is_file())
            data['semanticWindows'][0]['render']['anchorIds']=['missing'];source.write_text(json.dumps(data))
            with patch.object(adapter.subprocess,'run'),self.assertRaisesRegex(ValueError,'real window anchors'):
                adapter.prepare(p)
            audio.write_bytes(b'changed')
            with patch.object(adapter.subprocess,'run'),self.assertRaisesRegex(ValueError,'hash changed'):
                adapter.prepare(p)

if __name__=='__main__':
    unittest.main()
