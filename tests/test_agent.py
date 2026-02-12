from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from timberline.agent import (
    DEFAULT_CONTEXT_FILE,
    KNOWN_AGENTS,
    buildContextBlock,
    buildEnvVars,
    detectInstalledAgents,
    encodeClaudePath,
    getAgentDef,
    injectAgentContext,
    launchAgent,
    linkProjectSession,
    unlinkProjectSession,
    validateAgentBinary,
)
from timberline.models import WorktreeInfo


def _makeInfo(name: str = "obsidian") -> WorktreeInfo:
    return WorktreeInfo(
        name=name,
        branch=f"nik/feature/{name}",
        base_branch="main",
        type="feature",
        path=f"/global/.timberline/projects/repo/worktrees/{name}",
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
    block = buildContextBlock(info, [info, *others], "myproject")
    assert "obsidian" in block
    assert "nik/feature/obsidian" in block
    assert "alpha" in block
    assert "beta" in block
    assert "myproject" in block
    assert "<!-- timberline:start -->" in block
    assert "<!-- timberline:end -->" in block
    # should NOT reference main repo path
    assert "Main repo" not in block
    assert "Project" in block


def test_buildContextBlock_guidelines():
    info = _makeInfo()
    block = buildContextBlock(info, [info], "proj")
    assert "MUST stay within this directory" in block
    assert "Do NOT write files outside" in block


def test_injectAgentContext_new_file(tmp_path: Path):
    info = _makeInfo()
    agent = KNOWN_AGENTS["claude"]
    injectAgentContext(agent, tmp_path, info, [info], "myproject")
    content = (tmp_path / ".claude" / "rules" / "worktrees.md").read_text()
    assert "<!-- timberline:start -->" in content
    assert "obsidian" in content


def test_injectAgentContext_existing_without_markers(tmp_path: Path):
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "worktrees.md").write_text("# Existing content\n")
    info = _makeInfo()
    agent = KNOWN_AGENTS["claude"]
    injectAgentContext(agent, tmp_path, info, [info], "myproject")
    content = (rules_dir / "worktrees.md").read_text()
    assert "# Existing content" in content
    assert "<!-- timberline:start -->" in content


def test_injectAgentContext_replaces_existing_markers(tmp_path: Path):
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "worktrees.md").write_text(
        "# Header\n<!-- timberline:start -->\nold content\n<!-- timberline:end -->\n# Footer\n"
    )
    info = _makeInfo()
    agent = KNOWN_AGENTS["claude"]
    injectAgentContext(agent, tmp_path, info, [info], "myproject")
    content = (rules_dir / "worktrees.md").read_text()
    assert "old content" not in content
    assert "obsidian" in content
    assert "# Header" in content
    assert "# Footer" in content


def test_injectAgentContext_creates_parent_dirs(tmp_path: Path):
    info = _makeInfo()
    agent = KNOWN_AGENTS["claude"]
    assert not (tmp_path / ".claude").exists()
    injectAgentContext(agent, tmp_path, info, [info], "myproject")
    assert (tmp_path / ".claude" / "rules" / "worktrees.md").exists()


def test_injectAgentContext_codex_uses_agents_md(tmp_path: Path):
    info = _makeInfo()
    agent = KNOWN_AGENTS["codex"]
    injectAgentContext(agent, tmp_path, info, [info], "myproject")
    assert (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".claude").exists()
    content = (tmp_path / "AGENTS.md").read_text()
    assert "obsidian" in content


def test_getAgentDef_known():
    agent = getAgentDef("claude")
    assert agent.binary == "claude"
    assert agent.context_file == ".claude/rules/worktrees.md"


def test_getAgentDef_gemini():
    agent = getAgentDef("gemini")
    assert agent.binary == "gemini"
    assert agent.context_file == "GEMINI.md"


def test_getAgentDef_unknown_returns_default():
    agent = getAgentDef("cc")
    assert agent.binary == "cc"
    assert agent.context_file == DEFAULT_CONTEXT_FILE


def test_getAgentDef_unknown_with_override():
    agent = getAgentDef("z", context_file_override="Z.md")
    assert agent.binary == "z"
    assert agent.context_file == "Z.md"


def test_getAgentDef_known_with_override():
    agent = getAgentDef("claude", context_file_override="CUSTOM.md")
    assert agent.binary == "claude"
    assert agent.context_file == "CUSTOM.md"


def test_getAgentDef_known_no_override():
    agent = getAgentDef("claude")
    assert agent.context_file == ".claude/rules/worktrees.md"


def test_validateAgentBinary_known_found():
    with patch("timberline.agent.shutil.which", return_value="/usr/bin/claude"):
        assert validateAgentBinary("claude") == "/usr/bin/claude"


def test_validateAgentBinary_unknown_found():
    with patch("timberline.agent.shutil.which", return_value="/usr/bin/cc"):
        assert validateAgentBinary("cc") == "/usr/bin/cc"


def test_validateAgentBinary_not_found():
    with patch("timberline.agent.shutil.which", return_value=None):
        assert validateAgentBinary("nonexistent") is None


def test_detectInstalledAgents_none():
    with patch("timberline.agent.shutil.which", return_value=None):
        assert detectInstalledAgents() == []


def test_detectInstalledAgents_some():
    def mock_which(binary: str) -> str | None:
        return "/usr/bin/claude" if binary == "claude" else None

    with patch("timberline.agent.shutil.which", side_effect=mock_which):
        result = detectInstalledAgents()
        assert result == ["claude"]


# ─── Session linking ──────────────────────────────────────────────────────────


def test_encodeClaudePath():
    assert encodeClaudePath("/Users/n/Projects/Foo") == "-Users-n-Projects-Foo"
    assert encodeClaudePath("/a/b.c d/e") == "-a-b-c-d-e"


def test_encodeClaudePath_dots_and_spaces():
    assert encodeClaudePath("/home/user/my project.v2") == "-home-user-my-project-v2"


def test_linkProjectSession_creates_symlink(tmp_path: Path):
    repo_root = tmp_path / "repo"
    wt_path = tmp_path / "worktree"
    repo_root.mkdir()
    wt_path.mkdir()

    with patch("timberline.agent.getClaudeProjectDir") as mock_dir:
        target = tmp_path / "claude" / "main"
        link = tmp_path / "claude" / "wt"
        mock_dir.side_effect = lambda p: link if p == str(wt_path) else target

        result = linkProjectSession("claude", wt_path, repo_root)

    assert result is True
    assert link.is_symlink()
    assert link.resolve() == target.resolve()


def test_linkProjectSession_skips_existing_real_dir(tmp_path: Path):
    repo_root = tmp_path / "repo"
    wt_path = tmp_path / "worktree"
    repo_root.mkdir()
    wt_path.mkdir()

    with patch("timberline.agent.getClaudeProjectDir") as mock_dir:
        target = tmp_path / "claude" / "main"
        link = tmp_path / "claude" / "wt"
        link.mkdir(parents=True)
        mock_dir.side_effect = lambda p: link if p == str(wt_path) else target

        result = linkProjectSession("claude", wt_path, repo_root)

    assert result is False
    assert not link.is_symlink()


def test_linkProjectSession_replaces_stale_symlink(tmp_path: Path):
    repo_root = tmp_path / "repo"
    wt_path = tmp_path / "worktree"
    repo_root.mkdir()
    wt_path.mkdir()

    with patch("timberline.agent.getClaudeProjectDir") as mock_dir:
        target = tmp_path / "claude" / "main"
        link = tmp_path / "claude" / "wt"
        link.parent.mkdir(parents=True)
        # create stale symlink pointing to nonexistent
        link.symlink_to(tmp_path / "nonexistent")
        mock_dir.side_effect = lambda p: link if p == str(wt_path) else target

        result = linkProjectSession("claude", wt_path, repo_root)

    assert result is True
    assert link.is_symlink()
    assert link.resolve() == target.resolve()


def test_linkProjectSession_already_correct(tmp_path: Path):
    repo_root = tmp_path / "repo"
    wt_path = tmp_path / "worktree"
    repo_root.mkdir()
    wt_path.mkdir()

    with patch("timberline.agent.getClaudeProjectDir") as mock_dir:
        target = tmp_path / "claude" / "main"
        link = tmp_path / "claude" / "wt"
        target.mkdir(parents=True)
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        mock_dir.side_effect = lambda p: link if p == str(wt_path) else target

        result = linkProjectSession("claude", wt_path, repo_root)

    assert result is False


def test_linkProjectSession_unknown_agent(tmp_path: Path):
    result = linkProjectSession("unknown-agent", tmp_path / "wt", tmp_path / "repo")
    assert result is False


def test_unlinkProjectSession_removes_symlink(tmp_path: Path):
    wt_path = tmp_path / "worktree"
    wt_path.mkdir()

    with patch("timberline.agent.getClaudeProjectDir") as mock_dir:
        link = tmp_path / "claude" / "wt"
        target = tmp_path / "claude" / "main"
        target.mkdir(parents=True)
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        mock_dir.return_value = link

        result = unlinkProjectSession("claude", wt_path)

    assert result is True
    assert not link.exists()


def test_unlinkProjectSession_noop_no_symlink(tmp_path: Path):
    wt_path = tmp_path / "worktree"
    wt_path.mkdir()

    with patch("timberline.agent.getClaudeProjectDir") as mock_dir:
        link = tmp_path / "claude" / "wt"
        mock_dir.return_value = link

        result = unlinkProjectSession("claude", wt_path)

    assert result is False


def test_unlinkProjectSession_unknown_agent(tmp_path: Path):
    result = unlinkProjectSession("unknown-agent", tmp_path / "wt")
    assert result is False


# ─── launchAgent with command override ────────────────────────────────────────


def test_launchAgent_default(tmp_path: Path):
    """launchAgent without command uses agent binary."""
    agent = KNOWN_AGENTS["claude"]
    with patch("timberline.agent.os.execvpe") as mock_exec, patch("timberline.agent.os.chdir"):
        launchAgent(agent, tmp_path, {})
        mock_exec.assert_called_once_with("claude", ["claude"], mock_exec.call_args[0][2])


def test_launchAgent_custom_command(tmp_path: Path):
    """launchAgent with command splits and execs the custom command."""
    agent = KNOWN_AGENTS["claude"]
    with patch("timberline.agent.os.execvpe") as mock_exec, patch("timberline.agent.os.chdir"):
        launchAgent(agent, tmp_path, {}, command="claude --dangerously-skip-permissions")
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert args[0] == "claude"
        assert args[1] == ["claude", "--dangerously-skip-permissions"]
