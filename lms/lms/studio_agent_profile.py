"""Optional Hub assignment guard for native Studio Agent read-only DocPerm rows.

A site without Hub, or an older Hub without the reviewed profile, denies this
role. Ordinary LMS users and Administrator keep the existing native path.
"""

from __future__ import annotations

import importlib

import frappe


def is_agent(user=None):
	user = user or frappe.session.user
	return user not in {"Guest", "Administrator"} and "Studio Agent" in set(frappe.get_roles(user) or [])


def load_profile():
	if "edu_hub" not in frappe.get_installed_apps():
		return None
	try:
		return importlib.import_module("edu_hub.studio_content.agent_profile")
	except ImportError:
		return None


def permission(doc, ptype="read", user=None):
	if not is_agent(user):
		return None
	if ptype not in (None, "read"):
		return False
	profile = load_profile()
	return bool(profile and profile.permission(doc, ptype, user))


def query(doctype, user=None):
	if not is_agent(user):
		return None
	profile = load_profile()
	return profile.query(doctype, user) if profile else "0=1"
