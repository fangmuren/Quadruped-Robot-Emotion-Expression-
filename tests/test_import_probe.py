import unittest

import bootstrap  # noqa: F401
from emotion import SixEmotions


class ImportProbeTest(unittest.TestCase):
    def test_imports_project_modules_without_manual_pythonpath(self):
        self.assertIn('happy', SixEmotions.ALL)


if __name__ == '__main__':
    unittest.main()
