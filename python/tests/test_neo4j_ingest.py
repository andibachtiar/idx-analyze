import os
import sys
from unittest.mock import MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# neo4j_ingest.py imports neo4j and dotenv at module level; mock them only for
# that import, then restore the real modules so other test files are unaffected.
_original_modules = {name: sys.modules.get(name) for name in ("neo4j", "dotenv")}
sys.modules["neo4j"] = MagicMock()
sys.modules["dotenv"] = MagicMock()

import unittest
from io import StringIO
from unittest.mock import patch

import neo4j_ingest

# Restore real modules now that neo4j_ingest is imported.
for name, module in _original_modules.items():
    if module is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = module


class TestNeo4jIngest(unittest.TestCase):
    def test_ingest_all_stock_profiles_file_not_found(self):
        """Test that ingest_all_stock_profiles handles FileNotFoundError gracefully."""
        # Using a path that definitely doesn't exist
        dummy_path = "non_existent_file_12345.json"

        # Capture stdout to verify the error message
        with patch('sys.stdout', new=StringIO()) as fake_out:
            # The function should catch FileNotFoundError and return None
            result = neo4j_ingest.ingest_all_stock_profiles(data_path=dummy_path)

            output = fake_out.getvalue().strip()
            self.assertIn(f"Error: Data file not found at {dummy_path}", output)
            self.assertIsNone(result)

    def test_ingest_all_stock_summaries_file_not_found(self):
        """Test that ingest_all_stock_summaries handles FileNotFoundError gracefully."""
        # Using a path that definitely doesn't exist
        dummy_path = "non_existent_file_12345.json"

        # Capture stdout to verify the error message
        with patch('sys.stdout', new=StringIO()) as fake_out:
            # The function should catch FileNotFoundError and return None
            result = neo4j_ingest.ingest_all_stock_summaries(data_path=dummy_path)

            output = fake_out.getvalue().strip()
            self.assertIn(f"Error: Data file not found at {dummy_path}", output)
            self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
