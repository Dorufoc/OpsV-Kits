from __future__ import annotations

import os
from pathlib import Path

import pathspec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern


class GitignoreParser:
    def __init__(self, root_dir: str):
        self._root_dir = os.path.abspath(root_dir)
        self._rules: dict[str, pathspec.PathSpec] = {}
        self._load_all_gitignore_files()

    def _load_all_gitignore_files(self) -> None:
        for dirpath, dirnames, filenames in os.walk(self._root_dir):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            if ".gitignore" in filenames:
                gitignore_path = os.path.join(dirpath, ".gitignore")
                relative_dir = os.path.relpath(dirpath, self._root_dir)
                self._load_gitignore(gitignore_path, relative_dir)

    def _load_gitignore(self, filepath: str, relative_dir: str) -> None:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
            patterns = [line for line in lines if line.strip() and not line.startswith("#")]
            if patterns:
                self._rules[relative_dir] = pathspec.PathSpec.from_lines(
                    GitWildMatchPattern, patterns
                )
        except Exception:
            pass

    def is_ignored(self, relative_path: str, is_dir: bool = False) -> bool:
        rel_path = relative_path.replace("\\", "/")
        if is_dir and not rel_path.endswith("/"):
            rel_path += "/"

        for rule_dir, spec in self._rules.items():
            rule_dir_normalized = rule_dir.replace("\\", "/")
            if rule_dir_normalized == ".":
                match_path = rel_path
            else:
                prefix = rule_dir_normalized + "/"
                if not rel_path.startswith(prefix) and rel_path != rule_dir_normalized:
                    continue
                if rel_path == rule_dir_normalized:
                    match_path = "."
                else:
                    match_path = rel_path[len(prefix):]
            if spec.match_file(match_path):
                return True
        return False

    def filter_files(self, file_list: list[tuple[str, bool]]) -> list[tuple[str, bool]]:
        return [(path, is_dir) for path, is_dir in file_list if not self.is_ignored(path, is_dir)]
