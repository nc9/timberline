from __future__ import annotations

from pathlib import Path

from timberline.init_deps import (
    detectInstaller,
    detectPreLand,
    findProjectDirs,
    isDifferentEcosystem,
)


def test_detectInstaller_bun(tmp_path: Path):
    (tmp_path / "bun.lock").write_text("")
    assert detectInstaller(tmp_path) == ["bun", "install"]


def test_detectInstaller_npm(tmp_path: Path):
    (tmp_path / "package-lock.json").write_text("{}")
    assert detectInstaller(tmp_path) == ["npm", "install"]


def test_detectInstaller_uv(tmp_path: Path):
    (tmp_path / "uv.lock").write_text("")
    (tmp_path / "pyproject.toml").write_text("")
    assert detectInstaller(tmp_path) == ["uv", "sync"]


def test_detectInstaller_requirements(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask")
    assert detectInstaller(tmp_path) == ["uv", "pip", "install", "-r", "requirements.txt"]


def test_detectInstaller_none(tmp_path: Path):
    assert detectInstaller(tmp_path) is None


def test_detectInstaller_priority(tmp_path: Path):
    """bun.lock takes priority over package-lock.json."""
    (tmp_path / "bun.lock").write_text("")
    (tmp_path / "package-lock.json").write_text("{}")
    assert detectInstaller(tmp_path) == ["bun", "install"]


def test_isDifferentEcosystem():
    assert isDifferentEcosystem(["bun", "install"], ["uv", "sync"])
    assert not isDifferentEcosystem(["bun", "install"], ["npm", "install"])
    assert not isDifferentEcosystem(["uv", "sync"], ["uv", "pip", "install"])
    assert isDifferentEcosystem(None, ["bun", "install"])


def test_findProjectDirs(tmp_path: Path):
    # root has bun
    (tmp_path / "package.json").write_text("{}")
    # subdir has python
    sub = tmp_path / "apps" / "ml"
    sub.mkdir(parents=True)
    (sub / "pyproject.toml").write_text("")

    dirs = findProjectDirs(tmp_path)
    assert sub in dirs


def test_findProjectDirs_skips_node_modules(tmp_path: Path):
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "package.json").write_text("{}")

    assert findProjectDirs(tmp_path) == []


def test_detectPreLand_makefile_check(tmp_path: Path):
    (tmp_path / "Makefile").write_text("check: fmt lint test\n")
    assert detectPreLand(tmp_path) == "make check"


def test_detectPreLand_package_json_check_bun(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts":{"check":"tsc && vitest"}}')
    (tmp_path / "bun.lock").write_text("")
    assert detectPreLand(tmp_path) == "bun run check"


def test_detectPreLand_package_json_check_npm(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts":{"check":"tsc && vitest"}}')
    assert detectPreLand(tmp_path) == "npm run check"


def test_detectPreLand_makefile_test_fallback(tmp_path: Path):
    (tmp_path / "Makefile").write_text("test:\n\tpytest\n")
    assert detectPreLand(tmp_path) == "make test"


def test_detectPreLand_package_json_test_fallback(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest"}}')
    assert detectPreLand(tmp_path) == "npm run test"


def test_detectPreLand_none(tmp_path: Path):
    assert detectPreLand(tmp_path) is None


def test_detectPreLand_check_over_test(tmp_path: Path):
    """check: takes priority over test:."""
    (tmp_path / "Makefile").write_text("check: fmt lint test\ntest:\n\tpytest\n")
    assert detectPreLand(tmp_path) == "make check"


# --- Cargo (Rust) ---


def test_detectInstaller_cargo_lock(tmp_path: Path):
    (tmp_path / "Cargo.lock").write_text("")
    assert detectInstaller(tmp_path) == ["cargo", "fetch"]


def test_detectInstaller_cargo_toml(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text("")
    assert detectInstaller(tmp_path) == ["cargo", "fetch"]


def test_detectInstaller_cargo_lock_priority(tmp_path: Path):
    """Cargo.lock takes priority over Cargo.toml."""
    (tmp_path / "Cargo.lock").write_text("")
    (tmp_path / "Cargo.toml").write_text("")
    assert detectInstaller(tmp_path) == ["cargo", "fetch"]


# --- Go ---


def test_detectInstaller_go_sum(tmp_path: Path):
    (tmp_path / "go.sum").write_text("")
    assert detectInstaller(tmp_path) == ["go", "mod", "download"]


def test_detectInstaller_go_mod(tmp_path: Path):
    (tmp_path / "go.mod").write_text("")
    assert detectInstaller(tmp_path) == ["go", "mod", "download"]


# --- Composer (PHP) ---


def test_detectInstaller_composer_lock(tmp_path: Path):
    (tmp_path / "composer.lock").write_text("{}")
    assert detectInstaller(tmp_path) == ["composer", "install"]


def test_detectInstaller_composer_json(tmp_path: Path):
    (tmp_path / "composer.json").write_text("{}")
    assert detectInstaller(tmp_path) == ["composer", "install"]


# --- Bundle (Ruby) ---


def test_detectInstaller_gemfile_lock(tmp_path: Path):
    (tmp_path / "Gemfile.lock").write_text("")
    assert detectInstaller(tmp_path) == ["bundle", "install"]


def test_detectInstaller_gemfile(tmp_path: Path):
    (tmp_path / "Gemfile").write_text("")
    assert detectInstaller(tmp_path) == ["bundle", "install"]


# --- isDifferentEcosystem expanded ---


def test_isDifferentEcosystem_rust_vs_js():
    assert isDifferentEcosystem(["cargo", "fetch"], ["bun", "install"])


def test_isDifferentEcosystem_go_vs_python():
    assert isDifferentEcosystem(["go", "mod", "download"], ["uv", "sync"])


def test_isDifferentEcosystem_php_vs_ruby():
    assert isDifferentEcosystem(["composer", "install"], ["bundle", "install"])


def test_isDifferentEcosystem_same_rust():
    assert not isDifferentEcosystem(["cargo", "fetch"], ["cargo", "fetch"])


def test_isDifferentEcosystem_same_go():
    assert not isDifferentEcosystem(["go", "mod", "download"], ["go", "mod", "download"])


def test_isDifferentEcosystem_unknown_command():
    assert isDifferentEcosystem(["unknown", "install"], ["bun", "install"])


# --- detectPreLand expanded ---


def test_detectPreLand_cargo(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text("")
    assert detectPreLand(tmp_path) == "cargo test"


def test_detectPreLand_go(tmp_path: Path):
    (tmp_path / "go.mod").write_text("")
    assert detectPreLand(tmp_path) == "go test ./..."


def test_detectPreLand_composer_check(tmp_path: Path):
    (tmp_path / "composer.json").write_text('{"scripts":{"check":"phpstan && phpunit"}}')
    assert detectPreLand(tmp_path) == "composer run-script check"


def test_detectPreLand_composer_test(tmp_path: Path):
    (tmp_path / "composer.json").write_text('{"scripts":{"test":"phpunit"}}')
    assert detectPreLand(tmp_path) == "composer run-script test"


def test_detectPreLand_makefile_over_cargo(tmp_path: Path):
    """Makefile takes priority over ecosystem defaults."""
    (tmp_path / "Makefile").write_text("check: clippy test\n")
    (tmp_path / "Cargo.toml").write_text("")
    assert detectPreLand(tmp_path) == "make check"


def test_detectPreLand_makefile_over_go(tmp_path: Path):
    """Makefile takes priority over ecosystem defaults."""
    (tmp_path / "Makefile").write_text("test:\n\tgo test ./...\n")
    (tmp_path / "go.mod").write_text("")
    assert detectPreLand(tmp_path) == "make test"


# --- findProjectDirs skip dirs ---


def test_findProjectDirs_skips_target(tmp_path: Path):
    t = tmp_path / "target" / "debug"
    t.mkdir(parents=True)
    (t / "Cargo.toml").write_text("")
    assert findProjectDirs(tmp_path) == []


def test_findProjectDirs_skips_vendor(tmp_path: Path):
    v = tmp_path / "vendor" / "pkg"
    v.mkdir(parents=True)
    (v / "composer.json").write_text("{}")
    assert findProjectDirs(tmp_path) == []


def test_findProjectDirs_skips_bundle(tmp_path: Path):
    b = tmp_path / ".bundle" / "gems"
    b.mkdir(parents=True)
    (b / "Gemfile").write_text("")
    assert findProjectDirs(tmp_path) == []
