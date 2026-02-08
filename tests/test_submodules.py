from __future__ import annotations

from pathlib import Path

from lumberjack.submodules import fixSubmoduleGitdirs, hasSubmodules


def test_hasSubmodules_false(tmp_path: Path):
    assert not hasSubmodules(tmp_path)


def test_hasSubmodules_true(tmp_path: Path):
    (tmp_path / ".gitmodules").write_text('[submodule "lib"]\n\tpath = lib\n\turl = https://x\n')
    assert hasSubmodules(tmp_path)


def test_fixSubmoduleGitdirs_no_gitmodules(tmp_path: Path):
    assert fixSubmoduleGitdirs(tmp_path) == 0
