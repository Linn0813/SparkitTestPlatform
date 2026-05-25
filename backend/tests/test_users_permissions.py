from __future__ import annotations

import inspect

from app.api.v1 import users as users_module
from app.core.deps import get_current_user, require_system_admin


def _dependency_callable(param):
    dep = param.default
    while hasattr(dep, "dependency"):
        dep = dep.dependency
    return dep


def test_list_users_allows_authenticated_read():
    sig = inspect.signature(users_module.list_users)
    assert _dependency_callable(sig.parameters["_"]) is get_current_user


def test_create_user_requires_system_admin():
    sig = inspect.signature(users_module.create_user)
    assert _dependency_callable(sig.parameters["_"]) is require_system_admin


def test_update_user_requires_system_admin():
    sig = inspect.signature(users_module.update_user)
    assert _dependency_callable(sig.parameters["_"]) is require_system_admin
