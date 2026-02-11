from __future__ import annotations

from pathlib import Path

import pytest

from timberline.shell import (
    _END_MARKER,
    _START_MARKER,
    generateShellInit,
    installShellInit,
    rcFilePath,
    uninstallShellInit,
)


def test_generateShellInit_bash():
    out = generateShellInit("bash")
    assert "tlcd()" in out
    assert "tln()" in out
    assert "tlc()" in out
    assert "tlh()" in out
    assert "tld()" in out
    assert "tl-prompt()" in out


def test_generateShellInit_zsh():
    out = generateShellInit("zsh")
    assert "tlcd()" in out
    assert "tln()" in out
    assert "tlc()" in out
    assert "tlh()" in out
    assert "tld()" in out
    assert "[[ -n" in out
    assert ".timberline/projects/" in out


def test_generateShellInit_fish():
    out = generateShellInit("fish")
    assert "function tlcd" in out
    assert "function tln" in out
    assert "function tlc" in out
    assert "function tlh" in out
    assert "function tld" in out
    assert "function tl-prompt" in out


def test_rcFilePath():
    assert rcFilePath("bash").name == ".bashrc"
    assert rcFilePath("zsh").name == ".zshrc"
    assert rcFilePath("fish").name == "config.fish"


def test_installShellInit_creates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("timberline.shell.rcFilePath", lambda s: tmp_path / ".zshrc")
    rc, changed = installShellInit("zsh")
    assert changed
    content = rc.read_text()
    assert _START_MARKER in content
    assert _END_MARKER in content
    assert "tlcd()" in content
    assert "tln()" in content


def test_installShellInit_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("timberline.shell.rcFilePath", lambda s: tmp_path / ".zshrc")
    installShellInit("zsh")
    _, changed = installShellInit("zsh")
    assert not changed


def test_installShellInit_appends_to_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    rc = tmp_path / ".bashrc"
    rc.write_text("# existing config\nexport FOO=bar\n")
    monkeypatch.setattr("timberline.shell.rcFilePath", lambda s: rc)
    _, changed = installShellInit("bash")
    assert changed
    content = rc.read_text()
    assert "export FOO=bar" in content
    assert _START_MARKER in content


def test_uninstallShellInit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("timberline.shell.rcFilePath", lambda s: tmp_path / ".zshrc")
    installShellInit("zsh")
    _, changed = uninstallShellInit("zsh")
    assert changed
    content = (tmp_path / ".zshrc").read_text()
    assert _START_MARKER not in content
    assert _END_MARKER not in content


def test_uninstallShellInit_no_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    rc = tmp_path / ".bashrc"
    rc.write_text("# just config\n")
    monkeypatch.setattr("timberline.shell.rcFilePath", lambda s: rc)
    _, changed = uninstallShellInit("bash")
    assert not changed


def test_uninstallShellInit_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("timberline.shell.rcFilePath", lambda s: tmp_path / ".missing")
    _, changed = uninstallShellInit("bash")
    assert not changed
