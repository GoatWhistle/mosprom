import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / '.claude/scripts'


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cleanup-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Template Maintainer')
        self.git('config', 'user.email', 'maintainer@example.test')
        shutil.copytree(SCRIPTS, self.root / '.claude/scripts', ignore=shutil.ignore_patterns('__pycache__'))
        self.write('.claude/scrub-paths', 'brief\nwork\nskills/\ndocs/adr/_template.md\n')
        self.write('AGENTS.md', 'Internal instructions\n')
        self.write('brief/TASK.md', 'Private material\n')
        self.write('work/plan.md', 'Private plan\n')
        self.write('skills/example/SKILL.md', 'Internal skill\n')
        self.write('docs/adr/_template.md', 'Internal template\n')
        self.write('docs/screens/_template.md', 'Internal screen spec\n')
        self.write('docs/audits/README.md', 'Internal audits\n')
        self.write('docs/design-decisions.md', '# Decisions\nPersistence uses transactions.\n')
        self.write('README.md', '# Product\n\n<!-- scrub:start -->\nClaude Code workflow\n<!-- scrub:end -->\n\n[Decisions](docs/design-decisions.md)\n\n- [Decision template](docs/adr/)\n')
        self.write('.dockerignore', '.claude/\nbrief/\nwork/\ncontext/\nskills/\nnode_modules\n')
        self.write('backend/src/app/main.py', 'value = 42\n')
        self.commit('feat: add product\n\nExplain the product behavior.')

    def git(self, *args, cwd=None):
        return self.command(['git', *args], cwd=cwd).stdout

    def command(self, args, cwd=None, check=True):
        env = dict(os.environ, UV_OFFLINE='1')
        result = subprocess.run(args, cwd=cwd or self.root, env=env, text=True, capture_output=True)
        if check and result.returncode:
            self.fail(f'{args[:3]}: {result.stdout}\n{result.stderr}')
        return result

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, message):
        self.git('add', '-A')
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '-q', '-m', message)

    def clean(self, *args, check=True):
        return self.command(['bash', '.claude/scripts/strip-ai.sh', *args], check=check)

    def test_dry_run_preserves_source(self):
        head = self.git('rev-parse', 'HEAD')
        before = (self.root / 'README.md').read_bytes()
        self.clean()
        self.assertEqual(head, self.git('rev-parse', 'HEAD'))
        self.assertEqual(before, (self.root / 'README.md').read_bytes())
        self.assertTrue((self.root / '.claude').is_dir())

    def test_apply_preserves_code_and_decisions(self):
        self.clean('--apply')
        self.assertEqual('value = 42\n', (self.root / 'backend/src/app/main.py').read_text())
        self.assertTrue((self.root / 'docs/design-decisions.md').is_file())
        self.assertEqual('node_modules\n', (self.root / '.dockerignore').read_text())
        self.assertNotIn('Claude', (self.root / 'README.md').read_text())
        for name in ['.claude', 'skills', 'brief', 'work', 'AGENTS.md']:
            self.assertFalse((self.root / name).exists())

    def test_external_symlink_refuses_before_mutation(self):
        external = Path(self.temp.name) / 'external.md'
        external.write_text('<!-- scrub:start -->\nClaude Code\n<!-- scrub:end -->\n')
        (self.root / 'README.md').unlink()
        (self.root / 'README.md').symlink_to(external)
        self.commit('fix: link document')
        for options in [(), ('--apply',), ('--apply', '--history')]:
            result = self.clean(*options, check=False)
            self.assertNotEqual(0, result.returncode)
            self.assertTrue((self.root / '.claude').is_dir())
            self.assertIn('Claude Code', external.read_text())

    def test_dangling_symlink_refuses(self):
        (self.root / 'missing.md').symlink_to('absent.md')
        self.commit('fix: link document')
        result = self.clean('--apply', check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertTrue((self.root / '.claude').is_dir())

    def test_unsafe_registry_refuses(self):
        self.write('.claude/scrub-paths', '../external\n')
        self.commit('fix: change paths')
        result = self.clean('--apply', check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('unsafe scrub path', result.stderr)

    def test_historical_tool_cache_names_are_neutralized(self):
        self.write('frontend/scripts/checks/files.ts', 'const directories = [".impeccable"]\n')
        self.write('frontend/tests/scripts/checks/engine.test.ts', 'const path = "src/.impeccable/cache.json"\n')
        self.commit('test: check hidden directories')
        self.write('frontend/scripts/checks/files.ts', 'const directories = []\n')
        self.write('frontend/tests/scripts/checks/engine.test.ts', 'const path = "src/.cache/cache.json"\n')
        self.commit('refactor: simplify hidden directory checks')
        self.clean('--apply', '--history')
        for revision in self.git('rev-list', '--all').splitlines():
            paths = self.git('ls-tree', '-r', '--name-only', revision).splitlines()
            for rel in ['frontend/scripts/checks/files.ts', 'frontend/tests/scripts/checks/engine.test.ts']:
                if rel in paths:
                    self.assertNotIn('.impeccable', self.git('show', f'{revision}:{rel}'))
        self.assertEqual('const directories = []\n', (self.root / 'frontend/scripts/checks/files.ts').read_text())

    def add_tag(self):
        self.git('-c', 'user.name=Codex', '-c', 'user.email=codex@example.test', 'tag', '-a', 'v1', '-m', 'Release notes\n\nGenerated with Codex\nCo-authored-by: Codex <codex@example.test>')

    def assert_history_clean(self, root):
        self.assertEqual('', self.git('log', '--all', '--format=%b', cwd=root).strip())
        paths = self.git('log', '--all', '--format=', '--name-only', cwd=root)
        self.assertNotIn('docs/screens/', paths)
        self.assertNotIn('docs/audits/', paths)
        self.assertNotIn('docs/adr/', paths)
        self.assertNotIn('Codex', self.git('for-each-ref', '--format=%(taggername) %(taggeremail) %(contents)', 'refs/tags', cwd=root))
        self.assertIn('Release notes', self.git('cat-file', '-p', 'v1', cwd=root))
        for revision in self.git('rev-list', '--all', cwd=root).splitlines():
            text = self.git('show', f'{revision}:README.md', cwd=root)
            self.assertNotIn('Claude', text)
            self.assertNotIn('scrub:', text)
            self.assertNotIn('](docs/adr/)', text)
            paths = self.git('ls-tree', '-r', '--name-only', revision, cwd=root).splitlines()
            self.assertTrue(all(not p.startswith(('.claude/', 'brief/', 'work/', 'skills/')) for p in paths))

    def test_history_cleans_tags_bodies_and_blobs(self):
        self.add_tag()
        self.clean('--apply', '--history')
        self.assert_history_clean(self.root)

    def test_export_uses_same_rules_without_changing_source(self):
        self.add_tag()
        head = self.git('rev-parse', 'HEAD')
        out = Path(self.temp.name) / 'clean.git'
        self.command(['bash', '.claude/scripts/scrub-history.sh', str(self.root), str(out)])
        self.assert_history_clean(out)
        self.assertEqual(head, self.git('rev-parse', 'HEAD'))
        self.assertTrue((self.root / '.claude').is_dir())


if __name__ == '__main__':
    unittest.main()
