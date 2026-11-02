import importlib.util,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def bridge(monkeypatch):
 f=SimpleNamespace(session=SimpleNamespace(user='agent'),get_roles=lambda _:['Studio Agent'],get_installed_apps=lambda:[])
 monkeypatch.setitem(sys.modules,'frappe',f)
 spec=importlib.util.spec_from_file_location('lms_agent_bridge_test',ROOT/'lms/lms/studio_agent_profile.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 return f,m


def test_no_hub_or_profile_means_no_agent_access(bridge):
 f,m=bridge
 assert m.permission({'doctype':'Course Lesson'},'read') is False
 assert m.query('Course Chapter')=='0=1'
 f.get_installed_apps=lambda:['edu_hub']
 assert m.permission({'doctype':'Course Lesson'},'read') is False


def test_normal_users_and_automatic_admin_keep_native_path(bridge):
 f,m=bridge;f.session.user='Administrator'
 assert m.permission({},'write') is None and m.query('Course Lesson') is None
 f.session.user='teacher';f.get_roles=lambda _:['Course Creator']
 assert m.permission({},'read') is None


def test_only_hub_validated_assignment_is_delegated(bridge,monkeypatch):
 f,m=bridge;f.get_installed_apps=lambda:['edu_hub']
 profile=SimpleNamespace(permission=lambda doc,ptype,user:doc.get('name')=='L' and ptype=='read',query=lambda dt,user:'assigned_'+dt)
 monkeypatch.setattr(m,'load_profile',lambda:profile)
 assert m.permission({'name':'L'},'read') is True
 assert m.permission({'name':'OTHER'},'read') is False
 assert m.permission({'name':'L'},'write') is False
 assert m.query('Course Lesson')=='assigned_Course Lesson'


def test_native_profile_is_read_only_without_custom_permissions():
 for name in ['course_chapter','course_lesson']:
  d=json.loads((ROOT/f'lms/lms/doctype/{name}/{name}.json').read_text())
  rows=[r for r in d['permissions'] if r['role']=='Studio Agent']
  assert rows==[{'read':1,'role':'Studio Agent'}]
