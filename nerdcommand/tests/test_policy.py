"""Policy engine tests."""
from app.core.policy import requires_approval
from app.models.schemas import AgentManifest


def test_read_permission_not_gated():
    assert requires_approval("read:web") is False


def test_external_action_gated():
    assert requires_approval("send:message") is True
    assert requires_approval("publish:social") is True
    assert requires_approval("deploy") is True


def test_financial_and_destructive_gated():
    assert requires_approval("financial:pay") is True
    assert requires_approval("delete") is True
    assert requires_approval("admin") is True


def test_manifest_validates():
    m = AgentManifest.model_validate({
        "id": "x", "display_name": "X", "purpose": "test",
        "tools": ["web_search"], "permissions": ["read:web"],
    })
    assert m.id == "x"
