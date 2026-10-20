import unittest
from gcc_clang import Diagnostic, parse_line
from extract_features import extract_features, extract_for_commit, parse_unified_diff


def diff(path, old, new):
    return (f'diff --git a/{path} b/{path}\n'
            f'--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{old}\n+{new}\n')


class ExtractFeaturesTests(unittest.TestCase):
    def test_file_match(self):
        d = Diagnostic('syntax', 'error', 'expected ;', file='src/main.c')
        self.assertEqual(extract_for_commit([d], diff('src/main.c', 'x', 'y')).file, 1)
        self.assertEqual(extract_for_commit([d], diff('src/other.c', 'x', 'y')).file, 0)

    def test_symbol_only_changed_lines(self):
        d = Diagnostic('symbol', 'error', 'undeclared', symbol='parse_config')
        self.assertEqual(extract_for_commit([d], diff('src/p.c', 'parse_config();', 'run();')).symbol, 1)
        self.assertEqual(extract_for_commit([d], diff('src/p.c', 'parse_configuration();', 'run();')).symbol, 0)
        self.assertEqual(extract_for_commit([d], 'diff --git a/x.c b/x.c\n@@ -1 +1 @@\n context parse_config\n-old\n+new\n').symbol, 0)

    def test_missing_is_not_negative(self):
        d = Diagnostic('other', 'error', 'unknown failure')
        self.assertEqual(extract_for_commit([d], diff('x.c', 'a', 'b')).to_dict(),
                         {'file': None, 'symbol': None, 'build': None})

    def test_build_relevant(self):
        d = Diagnostic('linker', 'error', 'undefined reference', symbol='foo')
        self.assertEqual(extract_for_commit([d], diff('CMakeLists.txt', 'a', 'b')).build, 1)
        self.assertEqual(extract_for_commit([d], diff('README.md', 'a', 'b')).build, 0)
        d2 = Diagnostic('syntax', 'error', 'expected ;', file='x.c')
        self.assertIsNone(extract_for_commit([d2], diff('CMakeLists.txt', 'a', 'b')).build)

    def test_rename(self):
        patch = 'diff --git a/old.c b/new.c\nrename from old.c\nrename to new.c\n'
        d = Diagnostic('other', 'error', 'fail', file='new.c')
        self.assertEqual(extract_for_commit([d], patch).file, 1)

    def test_compiler_integration(self):
        d = parse_line("src/main.c:12:5: error: use of undeclared identifier 'foo'")
        result = extract_features([d], {'abc': diff('src/main.c', 'int x;', 'foo();')})
        self.assertEqual(result['abc'], {'file': 1, 'symbol': 1, 'build': None})

    def test_multiple_commits(self):
        d = Diagnostic('linker', 'error', 'undefined reference', symbol='parse_config')
        result = extract_features([d], {
            'a1': diff('src/parser.c', 'parse_config()', 'parse_cfg()'),
            'b2': diff('CMakeLists.txt', 'target_link_libraries(a parser)', 'target_link_libraries(a utils)'),
            'c3': diff('README.md', 'old', 'new'),
        })
        self.assertEqual(result['a1'], {'file': None, 'symbol': 1, 'build': 0})
        self.assertEqual(result['b2'], {'file': None, 'symbol': 0, 'build': 1})
        self.assertEqual(result['c3'], {'file': None, 'symbol': 0, 'build': 0})

    def test_empty_diagnostics(self):
        self.assertEqual(extract_for_commit([], diff('x.c', 'a', 'b')).to_dict(),
                         {'file': None, 'symbol': None, 'build': None})


if __name__ == '__main__':
    unittest.main()
