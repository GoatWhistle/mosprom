import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/context_budget.py'
SPEC = importlib.util.spec_from_file_location('context_budget', SCRIPT)
BUDGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUDGET)


class ContextTests(unittest.TestCase):
    def files(self):
        return {name: '# Empty template\n' for name in BUDGET.BUDGET}

    def test_missing_file_fails(self):
        files = self.files()
        del files['context/SESSION.md']
        self.assertIn('required file is missing', BUDGET.problems(files)[0])

    def test_extra_file_fails(self):
        files = self.files()
        files['context/rules.md'] = 'Rules'
        self.assertIn('not allowed', BUDGET.problems(files)[0])

    def test_protected_instructions_have_soft_target(self):
        files = self.files()
        instructions = '## Explicit user instructions\n\n' + 'Keep this instruction word for word.\n' * 250
        files['context/SESSION.md'] = '# Session\n\n' + instructions + '\n## Current state\n\nContinue.\n'
        self.assertEqual([], BUDGET.problems(files))
        self.assertTrue(BUDGET.notices(files))
        self.assertEqual(instructions + '\n', BUDGET.protected_instructions(files['context/SESSION.md']))

    def test_mutable_overflow_fails(self):
        files = self.files()
        files['context/SESSION.md'] = '## Explicit user instructions\nKeep.\n\n## Current state\n' + 'x' * 6001
        self.assertTrue(BUDGET.problems(files))

    def test_plain_overflow_fails(self):
        files = self.files()
        files['context/README.md'] = 'x' * 6001
        self.assertTrue(BUDGET.problems(files))


if __name__ == '__main__':
    unittest.main()
