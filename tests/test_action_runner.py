import os
import tempfile
import unittest
from unittest.mock import patch

import action_runner


class TestActionRunner(unittest.TestCase):
    def test_writes_report_for_ranked_commits(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = os.path.join(directory, 'summary.md')
            variables = {
                'GITHUB_WORKSPACE': directory,
                'BAYESCI_REPOSITORY': 'example/repo',
                'BAYESCI_WORKFLOW': '42',
                'BAYESCI_BRANCH': 'main',
                'BAYESCI_FAILED_SHA': 'f' * 40,
                'BAYESCI_RUN_ID': '1234',
                'GITHUB_STEP_SUMMARY': summary,
            }
            sha1, sha2 = '1' * 40, '2' * 40
            with patch.dict(os.environ, variables), \
                    patch.object(action_runner, 'get_last_good', return_value='0' * 40), \
                    patch.object(action_runner, 'get_commits_since', return_value=[sha1, sha2]), \
                    patch.object(action_runner, 'get_failed_log', return_value='error: missing file'), \
                    patch.object(action_runner, 'get_likelihoods', return_value=[0.2, 1.0]), \
                    patch.object(action_runner, 'get_probs', return_value={sha2: 0.83, sha1: 0.17}):
                result = action_runner.run()
            self.assertAlmostEqual(result[sha2], 0.83)
            with open(summary, encoding='utf8') as stream:
                report = stream.read()
            self.assertIn('https://github.com/example/repo/commit/' + sha2, report)
            self.assertIn('83.0%', report)
            self.assertIn('not calibrated', report)


if __name__ == '__main__':
    unittest.main()
