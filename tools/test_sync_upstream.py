"""Regression tests for real upstream merges, conflict rollback and history bundles."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from sync_upstream import prepare, git, REPOS


class UpstreamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.upstream = self.base / 'upstream'
        self.upstream.mkdir()
        git(self.upstream, 'init', '-b', 'main')
        self.identity(self.upstream)
        (self.upstream / 'sample.txt').write_text('baseline\n')
        git(self.upstream, 'add', '.')
        git(self.upstream, 'commit', '-m', 'baseline')
        self.baseline = git(self.upstream, 'rev-parse', 'HEAD').stdout.strip()
        self.root = self.base / 'fork'
        subprocess.run(['git', 'clone', str(self.upstream), str(self.root)], check=True, capture_output=True)
        self.identity(self.root)
        self.state = {key: {'repo': repo, 'commit': self.baseline} for key, repo in REPOS.items()}
        (self.root / 'upstream-lock.json').write_text(json.dumps(self.state))
        (self.root / 'UPSTREAM-STATUS.md').write_text('Baseline\n')
        (self.root / 'arm64.txt').write_text('keep this adaptation\n')
        self.commit(self.root, 'ARM64 adaptation')
        self.remotes = {key: str(self.upstream) for key in REPOS}
        self.destination = self.base / 'candidate'

    @staticmethod
    def identity(root):
        git(root, 'config', 'user.name', 'Test')
        git(root, 'config', 'user.email', 'test@example.invalid')

    @staticmethod
    def commit(root, message):
        git(root, 'add', '.')
        git(root, 'commit', '-m', message)

    def test_no_change_produces_no_candidate(self):
        self.assertEqual(prepare(self.root, self.destination, self.remotes), (False, False))
        self.assertFalse(self.destination.exists())

    def test_merge_retains_adaptation_and_bundles_complete_history(self):
        (self.upstream / 'sample.txt').write_text('upstream improvement\n')
        self.commit(self.upstream, 'upstream improvement')
        head = git(self.upstream, 'rev-parse', 'HEAD').stdout.strip()
        self.assertEqual(prepare(self.root, self.destination, self.remotes), (True, False))
        self.assertEqual((self.root / 'arm64.txt').read_text(), 'keep this adaptation\n')
        self.assertEqual((self.root / 'sample.txt').read_text(), 'upstream improvement\n')
        git(self.root, 'merge-base', '--is-ancestor', head, 'HEAD')
        restored = self.base / 'restored'
        subprocess.run(['git', 'clone', str(self.destination / 'candidate.bundle'), str(restored)],
                       check=True, capture_output=True)
        self.assertEqual((restored / 'arm64.txt').read_text(), 'keep this adaptation\n')
        self.assertEqual(git(restored, 'rev-parse', 'HEAD').stdout, git(self.root, 'rev-parse', 'HEAD').stdout)

    def test_conflict_restores_source_and_does_not_advance_windows_baseline(self):
        (self.root / 'sample.txt').write_text('ARM64-specific line\n')
        self.commit(self.root, 'local source change')
        (self.upstream / 'sample.txt').write_text('conflicting upstream line\n')
        self.commit(self.upstream, 'conflicting source change')
        self.assertEqual(prepare(self.root, self.destination, self.remotes), (True, True))
        self.assertEqual((self.root / 'sample.txt').read_text(), 'ARM64-specific line\n')
        state = json.loads((self.root / 'upstream-lock.json').read_text())
        self.assertEqual(state['windows']['commit'], self.baseline)
        self.assertIn('sample.txt', (self.destination / 'conflicts.patch').read_text())
        self.assertIn('draft tracking PR', (self.destination / 'pr-body.md').read_text())
        self.assertEqual(git(self.root, 'status', '--porcelain').stdout, '')


if __name__ == '__main__':
    unittest.main()
