from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from timberline.agent import (
    KNOWN_AGENTS,
    buildContextBlock,
    buildEnvVars,
    detectInstalledAgents,
    getAgentDef,
    injectAgentContext,
)
from timberline.types import WorktreeInfo


def _makeInfo(name: str = "obsidian") -> WorktreeInfo:
    return WorktreeInfo(
        name=name,
        branch=f"nik/feature/{name}",
        base_branch="main",
        type="feature",
        path=f"/repo/.tl/{name}",
    )


def test_buildEnvVars():
    info = _makeInfo()
    env = buildEnvVars(info, Path("/repo"))
    assert env["TL_WORKTREE"] == "obsidian"
    assert env["TL_BRANCH"] == "nik/feature/obsidian"
    assert env["TL_BASE"] == "main"
    assert env["TL_ROOT"] == "/repo"
    assert env["TL_TYPE"] == "feature"


def test_buildContextBlock():
    info = _makeInfo()
    others = [_makeInfo("alpha"), _makeInfo("beta")]
    block = buildContextBlock(info, [info, *others], Path("/repo"))
    assert "obsidian" in block
    assert "nik/feature/obsidian" in block
    assert "alpha" in block
    assert "beta" in block
    assert "<!-- timberline:start -->" in block
    assert "<!-- timberline:end -->" in block


def test_injectAgentContext_new_file(tmp_path: Path):
    info = _makeInfo()
    agent = KNOWN_AGENTS["claude"]
    injectAgentContext(agent, tmp_path, info, [info], Path("/repo"))
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "<!-- timberline:start -->" in content
    assert "obsidian" in content


def test_injectAgentContext_existing_without_markers(tmp_path: Path):
    (tmp_path / "CLAUDE.md").write_text("# Existing content\n")
    info = _makeInfo()
    agent = KNOWN_AGENTS["claude"]
    injectAgentContext(agent, tmp_path, info, [info], Path("/repo"))
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "# Existing content" in content
    assert "<!-- timberline:start -->" in content


def test_injectAgentContext_replaces_existing_markers(tmp_path: Path):
    (tmp_path / "CLAUDE.md").write_text(
        "# Header\n<!-- timberline:start -->\nold content\n<!-- timberline:end -->\n# Footer\n"
    )
    info = _makeInfo()
    agent = KNOWN_AGENTS["claude"]
    injectAgentContext(agent, tmp_path, info, [info], Path("/repo"))
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "old content" not in content
    assert "obsidian" in content
    assert "# Header" in content
    assert "# Footer" in content


def test_injectAgentContext_codex_uses_agents_md(tmp_path: Path):
    info = _makeInfo()
    agent = KNOWN_AGENTS["codex"]
    injectAgentContext(agent, tmp_path, info, [info], Path("/repo"))
    assert (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    content = (tmp_path / "AGENTS.md").read_text()
    assert "obsidian" in content


def test_getAgentDef_known():
    agent = getAgentDef("claude")
    assert agent.binary == "claude"
    assert agent.context_file == "CLAUDE.md"


def test_getAgentDef_unknown():
    with pytest.raises(KeyError, match="Unknown agent"):
        getAgentDef("nonexistent")


def test_detectInstalledAgents_none():
    with patch("timberline.agent.shutil.which", return_value=None):
        assert detectInstalledAgents() == []


def test_detectInstalledAgents_some():
    def mock_which(binary: str) -> str | None:
        return "/usr/bin/claude" if binary == "claude" else None

    with patch("timberline.agent.shutil.which", side_effect=mock_which):
        result = detectInstalledAgents()
        assert result == ["claude"]
