import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
class SyntaxTests(unittest.TestCase):
    def test_all_python_files_parse(self):
        for path in ROOT.rglob('*.py'):
            if '.git' not in path.parts: ast.parse(path.read_text(),filename=str(path))
if __name__=='__main__': unittest.main()
