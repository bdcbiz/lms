import importlib.util
import os
import unittest
from unittest.mock import patch

from frappe.search.sqlite_search import SQLiteSearch


def load_sqlite_module():
	module_path = os.environ.get("LMS_SQLITE_MODULE")
	if module_path:
		spec = importlib.util.spec_from_file_location("lms_sqlite_under_test", module_path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return module

	from lms import sqlite

	return sqlite


class TestLearningSearchCompatibility(unittest.TestCase):
	def test_build_index_forwards_frappe_v16_options(self):
		sqlite = load_sqlite_module()
		search = sqlite.LearningSearch.__new__(sqlite.LearningSearch)

		with patch.object(SQLiteSearch, "build_index") as parent_build_index:
			search.build_index(batch_size=17, is_continuation=True)

		parent_build_index.assert_called_once_with(batch_size=17, is_continuation=True)


if __name__ == "__main__":
	unittest.main()
