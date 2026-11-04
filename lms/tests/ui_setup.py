"""Only the synthetic lms.test browser principal; no production role changes."""

import frappe


def prepare_browser_test_user():
	if frappe.local.site != "lms.test" or not frappe.conf.allow_tests:
		raise PermissionError("Browser principal setup requires the isolated lms.test fixture")
	email = "frappe@example.com"
	user = frappe.get_doc("User", email)
	before = {row.role for row in user.roles}
	if "Studio Agent" in before:
		user.set("roles", [row for row in user.roles if row.role != "Studio Agent"])
		user.save()
		frappe.clear_cache(user=email)
	assert "Studio Agent" not in frappe.get_roles(email)
	assert {row.role for row in user.roles} == before - {"Studio Agent"}
	return {"fixture": email, "restricted_agent_role": False}
