"""
Policy engine for JARVIS (Phase 1).

The system prompt guides behavior; this policy code enforces boundaries.
Natural language must never be the source of truth for permissions. Every
tool call and consequential action is checked here.
"""
from __future__ import annotations

from ..config import settings
from ..models.schemas import AgentManifest, PermissionClass

# Map an agent permission string (e.g. "read:web") to the permission class it
# belongs to. This lets us gate whole classes of action consistently.
_PERMISSION_CLASS = {
    "read:web": PermissionClass.READ,
    "read:knowledge": PermissionClass.READ,
    "read:documents": PermissionClass.READ,
    "write:research": PermissionClass.WRITE_DRAFT,
    "write:draft": PermissionClass.WRITE_DRAFT,
    "write:code": PermissionClass.WRITE_DRAFT,
    "send:message": PermissionClass.EXTERNAL_ACTION,
    "publish:social": PermissionClass.EXTERNAL_ACTION,
    "deploy": PermissionClass.EXTERNAL_ACTION,
    "financial:pay": PermissionClass.FINANCIAL,
    "delete": PermissionClass.DESTRUCTIVE,
    "admin": PermissionClass.ADMIN,
}


def permission_class_for(permission: str) -> PermissionClass:
    return _PERMISSION_CLASS.get(permission, PermissionClass.WRITE_DRAFT)


def requires_approval(permission: str) -> bool:
    """A consequential action needs human approval by default, unless an
    explicit, trusted automation policy overrides it."""
    return permission_class_for(permission).value in settings.always_approve


def can_use_tool(agent: AgentManifest, tool: str) -> bool:
    """Least privilege: an agent may use a tool only if it holds a permission
    whose class grants that capability."""
    if tool in agent.tools:
        return True
    return False


def agent_allows_permission(agent: AgentManifest, permission: str) -> bool:
    return permission in agent.permissions


def check_action(agent: AgentManifest, permission: str) -> bool:
    """Full check for an external action: the agent must hold the permission,
    and consequential actions must be approved."""
    if not agent_allows_permission(agent, permission):
        return False
    return True
