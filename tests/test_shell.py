from __future__ import annotations

from lumberjack.shell import generateShellInit


def test_generateShellInit_bash():
    out = generateShellInit("bash")
    assert "ljcd()" in out
    assert "lj-prompt()" in out


def test_generateShellInit_zsh():
    out = generateShellInit("zsh")
    assert "ljcd()" in out
    assert "[[ -n" in out


def test_generateShellInit_fish():
    out = generateShellInit("fish")
    assert "function ljcd" in out
    assert "function lj-prompt" in out
