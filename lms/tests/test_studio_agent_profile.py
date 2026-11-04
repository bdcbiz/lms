"""Pure bridge tests, also discovered by the native bench unittest runner."""

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class TestStudioAgentProfile(unittest.TestCase):
	def setUp(self):
		self.frappe = SimpleNamespace(
			PermissionError=PermissionError,
			session=SimpleNamespace(user="agent"),
			get_roles=lambda _: ["Studio Agent"],
			get_installed_apps=lambda: [],
		)
		self.context = patch.dict(sys.modules, {"frappe": self.frappe})
		self.context.start()
		spec = importlib.util.spec_from_file_location(
			"lms_agent_bridge_test", ROOT / "lms/lms/studio_agent_profile.py"
		)
		self.bridge = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(self.bridge)

	def tearDown(self):
		self.context.stop()

	def test_no_hub_or_profile_means_no_agent_access(self):
		f, m = self.frappe, self.bridge
		with self.assertRaises(PermissionError):
			m.permission({"doctype": "Course Lesson"}, "read")
		self.assertEqual(m.query("Course Chapter"), "0=1")
		f.get_installed_apps = lambda: ["edu_hub"]
		with patch.object(m, "load_profile", return_value=None):
			with self.assertRaises(PermissionError):
				m.permission({"doctype": "Course Lesson"}, "read")

	def test_normal_users_and_automatic_admin_keep_native_path(self):
		f, m = self.frappe, self.bridge
		f.session.user = "Administrator"
		self.assertIsNone(m.permission({}, "write"))
		self.assertIsNone(m.query("Course Lesson"))
		f.session.user = "teacher"
		f.get_roles = lambda _: ["Course Creator"]
		self.assertIsNone(m.permission({}, "read"))

	def test_only_hub_validated_assignment_is_delegated(self):
		f, m = self.frappe, self.bridge
		f.get_installed_apps = lambda: ["edu_hub"]
		profile = SimpleNamespace(
			permission=lambda doc, ptype, user: doc.get("name") == "L" and ptype == "read",
			native_permission=lambda doc, ptype, user: doc.get("name") == "L" and ptype == "read",
			query=lambda dt, user: "assigned_" + dt,
		)
		with patch.object(m, "load_profile", return_value=profile):
			self.assertTrue(m.permission({"name": "L"}, "read"))
			with self.assertRaises(PermissionError):
				m.permission({"name": "OTHER"}, "read")
			with self.assertRaises(PermissionError):
				m.permission({"name": "L"}, "write")
			self.assertEqual(m.query("Course Lesson"), "assigned_Course Lesson")

	def test_native_profile_is_read_only_without_custom_permissions(self):
		for name in ["course_chapter", "course_lesson"]:
			d = json.loads((ROOT / f"lms/lms/doctype/{name}/{name}.json").read_text())
			self.assertEqual(
				[r for r in d["permissions"] if r["role"] == "Studio Agent"],
				[{"read": 1, "role": "Studio Agent"}],
			)

	def test_missing_native_guard_cannot_fall_back_to_a_docshare(self):
		with patch.object(
			self.bridge, "load_profile", return_value=SimpleNamespace(permission=lambda *a: True)
		):
			with self.assertRaises(PermissionError):
				self.bridge.permission({"doctype": "Course Lesson"}, "read")

	def test_native_denial_and_write_denial_cannot_fall_back_to_a_docshare(self):
		profile = SimpleNamespace(permission=lambda *a: False, native_permission=lambda *a: False)
		with patch.object(self.bridge, "load_profile", return_value=profile):
			for mode in ("read", "write"):
				with self.subTest(mode=mode), self.assertRaises(PermissionError):
					self.bridge.permission({"doctype": "Course Lesson"}, mode)

	def test_only_native_hard_guard_is_used_for_an_allowed_read(self):
		calls = []
		profile = SimpleNamespace(
			permission=lambda *a: self.fail("Boolean guard permits DocShare fallback"),
			native_permission=lambda *a: calls.append(a) or True,
		)
		with patch.object(self.bridge, "load_profile", return_value=profile):
			doc = {"doctype": "Course Lesson", "name": "L"}
			self.assertTrue(self.bridge.permission(doc, "read", "agent"))
			self.assertEqual(calls, [(doc, "read", "agent")])
