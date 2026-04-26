"""Unit tests for role loading and assignment logic."""
import pytest
from src.api.roles import load_roles, assign_role, build_system_header

ROLES_PATH = "roles.json"


@pytest.fixture
def roles():
    return load_roles(ROLES_PATH)


class TestLoadRoles:
    def test_loads_list(self, roles):
        assert isinstance(roles, list)
        assert len(roles) > 0

    def test_each_role_has_required_fields(self, roles):
        for r in roles:
            assert "name" in r
            assert "description" in r
            assert "rules" in r
            assert isinstance(r["rules"], list)


class TestAssignRole:
    def test_assigns_when_no_agents(self, roles):
        role = assign_role(roles, active_agents=[])
        assert role["name"] in [r["name"] for r in roles]

    def test_preferred_role_honoured(self, roles):
        role = assign_role(roles, active_agents=[], preferred="qa")
        assert role["name"] == "qa"

    def test_preferred_role_honoured_even_when_occupied(self, roles):
        # Preferred role is always granted — no cap enforcement
        active = [{"role": "qa"}]
        role = assign_role(roles, active_agents=active, preferred="qa")
        assert role["name"] == "qa"

    def test_picks_least_populated_without_preference(self, roles):
        # With no preference, assign_role picks the role with fewest active agents
        active = [{"role": r["name"]} for r in roles]  # one agent in every role
        # Add extra agents to all roles except designer
        active += [{"role": r["name"]} for r in roles if r["name"] != "designer"]
        role = assign_role(roles, active_agents=active)
        assert role["name"] == "designer"


class TestBuildSystemHeader:
    def test_contains_role_name(self, roles):
        header = build_system_header(roles[0])
        assert roles[0]["name"].upper() in header

    def test_contains_all_rules(self, roles):
        role = roles[0]
        header = build_system_header(role)
        for rule in role["rules"]:
            assert rule in header

    def test_contains_universal_rules(self, roles):
        header = build_system_header(roles[0])
        assert "APPEND ONLY" in header
        assert "last message" in header.lower()
