import os
from unittest.mock import patch

import pytest

from app.core.gitignore_parser import GitignoreParser


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


@pytest.fixture
def parser(project_dir):
    return GitignoreParser(str(project_dir))


class TestGitignoreParserInit:
    def test_init_resolves_absolute_path(self, tmp_path):
        p = GitignoreParser(str(tmp_path))
        assert p._root_dir == os.path.abspath(str(tmp_path))

    def test_init_empty_rules_no_gitignore(self, tmp_path):
        p = GitignoreParser(str(tmp_path))
        assert p._rules == {}


class TestLoadGitignore:
    def test_loads_root_gitignore(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("*.log\nnode_modules/\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert "." in p._rules

    def test_loads_subdirectory_gitignore(self, project_dir):
        sub = project_dir / "src"
        sub.mkdir()
        gitignore = sub / ".gitignore"
        gitignore.write_text("*.tmp\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert any("src" in k for k in p._rules)

    def test_skips_dot_directories(self, project_dir):
        dot_dir = project_dir / ".hidden"
        dot_dir.mkdir()
        gitignore = dot_dir / ".gitignore"
        gitignore.write_text("*.log\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert not any(".hidden" in k for k in p._rules)

    def test_ignores_comment_lines(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("# comment\n*.log\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert "." in p._rules

    def test_ignores_blank_lines(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("\n\n*.log\n\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert "." in p._rules

    def test_no_rules_if_only_comments(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("# only comments\n# another\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p._rules == {}

    def test_handles_read_error_gracefully(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("*.log\n", encoding="utf-8")
        with patch("builtins.open", side_effect=PermissionError("denied")):
            p = GitignoreParser(str(project_dir))
            assert p._rules == {}


class TestIsIgnored:
    def test_ignored_file(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("*.log\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p.is_ignored("error.log") is True

    def test_not_ignored_file(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("*.log\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p.is_ignored("main.py") is False

    def test_ignored_directory(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("node_modules/\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p.is_ignored("node_modules", is_dir=True) is True

    def test_directory_without_trailing_slash(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("build/\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p.is_ignored("build", is_dir=True) is True

    def test_backslash_path_converted(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("*.log\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p.is_ignored("src\\error.log") is True

    def test_subdirectory_gitignore(self, project_dir):
        sub = project_dir / "src"
        sub.mkdir()
        gitignore = sub / ".gitignore"
        gitignore.write_text("*.tmp\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p.is_ignored("src/data.tmp") is True

    def test_subdirectory_gitignore_no_match_outside(self, project_dir):
        sub = project_dir / "src"
        sub.mkdir()
        gitignore = sub / ".gitignore"
        gitignore.write_text("*.tmp\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p.is_ignored("data.tmp") is False

    def test_no_rules_returns_false(self, tmp_path):
        p = GitignoreParser(str(tmp_path))
        assert p.is_ignored("anything.txt") is False

    def test_is_dir_adds_slash(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("dist/\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p.is_ignored("dist", is_dir=True) is True

    def test_nested_path(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("*.pyc\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p.is_ignored("src/app/__pycache__/module.pyc") is True

    def test_subdirectory_rule_dir_match(self, project_dir):
        sub = project_dir / "src"
        sub.mkdir()
        gitignore = sub / ".gitignore"
        gitignore.write_text("*.tmp\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        assert p.is_ignored("src", is_dir=True) is False


class TestFilterFiles:
    def test_filters_ignored_files(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("*.log\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        files = [
            ("main.py", False),
            ("error.log", False),
            ("debug.log", False),
        ]
        result = p.filter_files(files)
        assert len(result) == 1
        assert result[0] == ("main.py", False)

    def test_filters_ignored_directories(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("node_modules/\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        files = [
            ("src", True),
            ("node_modules", True),
        ]
        result = p.filter_files(files)
        assert len(result) == 1
        assert result[0] == ("src", True)

    def test_empty_list(self, tmp_path):
        p = GitignoreParser(str(tmp_path))
        result = p.filter_files([])
        assert result == []

    def test_no_rules_passes_all(self, tmp_path):
        p = GitignoreParser(str(tmp_path))
        files = [("a.txt", False), ("b.py", False)]
        result = p.filter_files(files)
        assert len(result) == 2

    def test_mixed_files_and_dirs(self, project_dir):
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("*.log\nbuild/\n", encoding="utf-8")
        p = GitignoreParser(str(project_dir))
        files = [
            ("main.py", False),
            ("error.log", False),
            ("build", True),
            ("src", True),
        ]
        result = p.filter_files(files)
        assert len(result) == 2
        paths = [r[0] for r in result]
        assert "main.py" in paths
        assert "src" in paths
