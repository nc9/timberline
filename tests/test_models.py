import warnings

import pytest
from pydantic import ValidationError

from timberline.models import (
    AgentConfig,
    AgentDef,
    BranchType,
    EnvConfig,
    InitConfig,
    NamingScheme,
    StateFile,
    SubmodulesConfig,
    TimberlineConfig,
    TimberlineError,
    WorktreeInfo,
)


def test_namingScheme_values():
    assert NamingScheme.MINERALS == "minerals"
    assert NamingScheme.CITIES == "cities"
    assert NamingScheme.COMPOUND == "compound"


def test_namingScheme_membership():
    assert "minerals" in NamingScheme._value2member_map_
    assert "bogus" not in NamingScheme._value2member_map_


def test_branchType_values():
    assert BranchType.FEATURE == "feature"
    assert BranchType.FIX == "fix"
    assert BranchType.HOTFIX == "hotfix"
    assert BranchType.CHORE == "chore"
    assert BranchType.REFACTOR == "refactor"


def test_timberlineConfig_defaults():
    cfg = TimberlineConfig()
    assert cfg.worktree_dir == ".tl"
    assert cfg.branch_template == "{user}/{type}/{name}"
    assert cfg.user == ""
    assert cfg.default_type == "feature"
    assert cfg.base_branch == "main"
    assert cfg.naming_scheme == NamingScheme.MINERALS
    assert cfg.init.auto_init is True
    assert cfg.env.auto_copy is True
    assert cfg.submodules.recursive is True
    assert cfg.agent.auto_launch is False
    assert cfg.default_agent == "claude"


def test_timberlineConfig_frozen():
    cfg = TimberlineConfig()
    with pytest.raises(ValidationError):
        cfg.user = "changed"  # type: ignore[misc]


def test_initConfig_defaults():
    ic = InitConfig()
    assert ic.init_command is None
    assert ic.auto_init is True
    assert ic.post_init == []


def test_envConfig_defaults():
    ec = EnvConfig()
    assert ec.auto_copy is True
    assert ".env" in ec.patterns
    assert "!.env.example" in ec.patterns
    assert ec.scan_depth == 3
    assert ec.scan_dirs is None


def test_submodulesConfig_frozen():
    sc = SubmodulesConfig()
    with pytest.raises(ValidationError):
        sc.auto_init = False  # type: ignore[misc]


def test_agentConfig_defaults():
    ac = AgentConfig()
    assert ac.auto_launch is False
    assert ac.inject_context is True
    assert ac.context_file is None


def test_agentConfig_frozen():
    ac = AgentConfig()
    with pytest.raises(ValidationError):
        ac.inject_context = False  # type: ignore[misc]


def test_agentDef_frozen():
    ad = AgentDef(binary="claude", context_file="CLAUDE.md")
    assert ad.binary == "claude"
    with pytest.raises(AttributeError):
        ad.binary = "other"  # type: ignore[misc]


def test_worktreeInfo_mutable():
    wt = WorktreeInfo(
        name="test", branch="main", base_branch="main", type="feature", path="/tmp/test"
    )
    wt.status = "3 modified"
    assert wt.status == "3 modified"


def test_worktreeInfo_defaults():
    wt = WorktreeInfo(
        name="test", branch="main", base_branch="main", type="feature", path="/tmp/test"
    )
    assert wt.created_at == ""
    assert wt.ahead == 0
    assert wt.behind == 0


def test_stateFile_defaults():
    sf = StateFile()
    assert sf.version == 1
    assert sf.repo_root == ""
    assert sf.worktrees == {}


def test_stateFile_frozen():
    sf = StateFile()
    with pytest.raises(AttributeError):
        sf.version = 2  # type: ignore[misc]


def test_timberlineError():
    err = TimberlineError("boom")
    assert str(err) == "boom"
    assert isinstance(err, Exception)


# ─── Pydantic validation tests ───────────────────────────────────────────────


def test_branchTemplate_validation():
    with pytest.raises(ValidationError, match="must contain \\{name\\}"):
        TimberlineConfig(branch_template="no-name-placeholder")


def test_scanDepth_validation():
    with pytest.raises(ValidationError, match="scan_depth must be >= 1"):
        EnvConfig(scan_depth=0)


def test_namingScheme_coercion():
    cfg = TimberlineConfig.model_validate({"naming_scheme": "cities"})
    assert cfg.naming_scheme == NamingScheme.CITIES


def test_invalidNamingScheme():
    with pytest.raises(ValidationError):
        TimberlineConfig.model_validate({"naming_scheme": "bogus"})


def test_unknownKey_warns():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        cfg = TimberlineConfig.model_validate({"unknown_field": "val", "user": "test"})
        assert cfg.user == "test"
        assert any("Unknown config key: 'unknown_field'" in str(warning.message) for warning in w)
