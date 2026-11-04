"""The broad browser fixture must not become a restricted mixed Studio Agent."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class TestBrowserPrincipal(unittest.TestCase):
	def load_helper(self, site="lms.test", allow=True):
		self.rows = [types.SimpleNamespace(role=r) for r in ["Moderator", "Studio Agent", "Course Creator"]]
		self.saved = 0
		doc = types.SimpleNamespace(roles=self.rows)
		doc.set = lambda field, rows: setattr(doc, field, rows)

		def save():
			self.saved += 1

		doc.save = save
		frappe = types.ModuleType("frappe")
		frappe.local = types.SimpleNamespace(site=site)
		frappe.conf = types.SimpleNamespace(allow_tests=allow)
		frappe.get_doc = lambda dt, name: doc
		frappe.clear_cache = lambda **kwargs: None
		frappe.get_roles = lambda user: [r.role for r in doc.roles] + ["All", "Guest"]
		spec = importlib.util.spec_from_file_location(
			"r88_browser_setup", Path(__file__).with_name("ui_setup.py")
		)
		module = importlib.util.module_from_spec(spec)
		with patch.dict(sys.modules, {"frappe": frappe}):
			spec.loader.exec_module(module)
		return module, doc

	def test_only_restricted_role_is_removed_from_synthetic_browser_principal(self):
		helper, doc = self.load_helper()
		helper.prepare_browser_test_user()
		self.assertEqual([r.role for r in doc.roles], ["Moderator", "Course Creator"])
		self.assertEqual(self.saved, 1)
		helper.prepare_browser_test_user()
		self.assertEqual(self.saved, 1)

	def test_refuses_any_production_or_non_test_site(self):
		for site, allow in [("hub.almadrasa.ai", True), ("lms.test", False)]:
			helper, doc = self.load_helper(site, allow)
			with self.assertRaises(PermissionError):
				helper.prepare_browser_test_user()
			self.assertEqual(self.saved, 0)
			self.assertIn("Studio Agent", [r.role for r in doc.roles])
