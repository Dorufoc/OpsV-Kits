import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.remote_executor import CommandResult


def _make_command_result(exit_code=0, stdout="", stderr=""):
    return CommandResult(exit_code=exit_code, stdout=stdout, stderr=stderr)


@pytest.fixture
def mock_executor():
    with patch("app.core.vite_project_detector.RemoteExecutor") as MockCls:
        mock = MagicMock()
        MockCls.return_value = mock
        mock.resolve_path.return_value = "/home/user/project"
        yield mock


@pytest.fixture
def detector(mock_executor):
    from app.core.vite_project_detector import ViteProjectDetector
    return ViteProjectDetector("test")


class TestViteProjectDetectorInit:
    def test_init_creates_executor(self):
        with patch("app.core.vite_project_detector.RemoteExecutor") as MockCls:
            from app.core.vite_project_detector import ViteProjectDetector
            ViteProjectDetector("myalias")
            MockCls.assert_called_once_with("myalias")

    def test_stores_account_alias(self, mock_executor):
        from app.core.vite_project_detector import ViteProjectDetector
        detector = ViteProjectDetector("myalias")
        assert detector._account_alias == "myalias"


class TestIsViteProject:
    def test_empty_path_raises(self, detector):
        from app.core.vite_project_detector import ViteProjectDetectorError
        with pytest.raises(ViteProjectDetectorError, match="项目路径不能为空"):
            detector.is_vite_project(project_path="")

    def test_no_vite_config_no_dependency(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["is_vite"] is False
        assert result["has_vite_config"] is False
        assert result["has_vite_dependency"] is False

    def test_has_vite_config_js(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="vite.config.js"),
            _make_command_result(exit_code=0, stdout=""),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["has_vite_config"] is True
        assert result["vite_config_file"] == "vite.config.js"
        assert result["is_vite"] is True

    def test_has_vite_config_ts(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="vite.config.ts"),
            _make_command_result(exit_code=0, stdout=""),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["has_vite_config"] is True
        assert result["vite_config_file"] == "vite.config.ts"

    def test_has_vite_config_mjs(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="vite.config.mjs"),
            _make_command_result(exit_code=0, stdout=""),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["has_vite_config"] is True

    def test_has_vite_config_cjs(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="vite.config.cjs"),
            _make_command_result(exit_code=0, stdout=""),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["has_vite_config"] is True

    def test_has_vite_config_mts(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="vite.config.mts"),
            _make_command_result(exit_code=0, stdout=""),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["has_vite_config"] is True

    def test_vite_dependency_in_dependencies(self, detector, mock_executor):
        pkg = json.dumps({"dependencies": {"vite": "^5.0.0"}})
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=pkg),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["has_vite_dependency"] is True
        assert result["vite_version"] == "^5.0.0"
        assert result["is_vite"] is True

    def test_vite_dependency_in_dev_dependencies(self, detector, mock_executor):
        pkg = json.dumps({"devDependencies": {"vite": "^4.3.0"}})
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=pkg),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["has_vite_dependency"] is True
        assert result["vite_version"] == "^4.3.0"

    def test_vite_dependency_prefers_deps_version(self, detector, mock_executor):
        pkg = json.dumps({
            "dependencies": {"vite": "^5.0.0"},
            "devDependencies": {"vite": "^4.0.0"},
        })
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=pkg),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["vite_version"] == "^5.0.0"

    def test_invalid_package_json(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout="not valid json{"),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["has_vite_dependency"] is False
        assert result["is_vite"] is False

    def test_config_check_fails(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["has_vite_config"] is False

    def test_package_check_fails(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=1, stdout=""),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["has_vite_dependency"] is False

    def test_both_config_and_dependency(self, detector, mock_executor):
        pkg = json.dumps({"devDependencies": {"vite": "^5.0.0"}})
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="vite.config.ts"),
            _make_command_result(exit_code=0, stdout=pkg),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["is_vite"] is True
        assert result["has_vite_config"] is True
        assert result["has_vite_dependency"] is True

    def test_different_account_alias(self, detector, mock_executor):
        from app.core.vite_project_detector import RemoteExecutor
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
        ]
        detector.is_vite_project(account_alias="other", project_path="/project")
        RemoteExecutor.assert_called_with("other")

    def test_same_account_alias_uses_default_executor(self, detector, mock_executor):
        from app.core.vite_project_detector import RemoteExecutor
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
        ]
        detector.is_vite_project(account_alias="test", project_path="/project")
        assert RemoteExecutor.call_count == 1

    def test_resolve_path_called(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
        ]
        detector.is_vite_project(project_path="~/project")
        mock_executor.resolve_path.assert_called_once_with("~/project")

    def test_multiline_config_output(self, detector, mock_executor):
        mock_executor.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="vite.config.js\nextra line"),
            _make_command_result(exit_code=0, stdout=""),
        ]
        result = detector.is_vite_project(project_path="/project")
        assert result["vite_config_file"] == "vite.config.js"


class TestDetectFramework:
    def test_empty_path_raises(self, detector):
        from app.core.vite_project_detector import ViteProjectDetectorError
        with pytest.raises(ViteProjectDetectorError, match="项目路径不能为空"):
            detector.detect_framework(project_path="")

    def test_no_package_json(self, detector, mock_executor):
        mock_executor.exec_command.return_value = _make_command_result(exit_code=1, stdout="")
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "unknown"
        assert result["has_react"] is False

    def test_empty_package_json(self, detector, mock_executor):
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout="")
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "unknown"

    def test_react_via_plugin(self, detector, mock_executor):
        pkg = json.dumps({"devDependencies": {"@vitejs/plugin-react": "^4.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "react"
        assert result["has_react"] is True

    def test_react_via_dependency(self, detector, mock_executor):
        pkg = json.dumps({"dependencies": {"react": "^18.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "react"
        assert result["has_react"] is True

    def test_vue_via_plugin(self, detector, mock_executor):
        pkg = json.dumps({"devDependencies": {"@vitejs/plugin-vue": "^5.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "vue"
        assert result["has_vue"] is True

    def test_vue_via_dependency(self, detector, mock_executor):
        pkg = json.dumps({"dependencies": {"vue": "^3.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "vue"

    def test_svelte_via_plugin(self, detector, mock_executor):
        pkg = json.dumps({"devDependencies": {"@vitejs/plugin-svelte": "^3.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "svelte"
        assert result["has_svelte"] is True

    def test_svelte_via_dependency(self, detector, mock_executor):
        pkg = json.dumps({"dependencies": {"svelte": "^4.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "svelte"

    def test_preact_via_plugin(self, detector, mock_executor):
        pkg = json.dumps({"devDependencies": {"@vitejs/plugin-preact": "^2.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "preact"
        assert result["has_preact"] is True

    def test_preact_via_dependency(self, detector, mock_executor):
        pkg = json.dumps({"dependencies": {"preact": "^10.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "preact"

    def test_solid_via_plugin(self, detector, mock_executor):
        pkg = json.dumps({"devDependencies": {"@vitejs/plugin-solid": "^2.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "solid"
        assert result["has_solid"] is True

    def test_solid_via_dependency(self, detector, mock_executor):
        pkg = json.dumps({"dependencies": {"solid-js": "^1.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "solid"

    def test_lit_via_plugin(self, detector, mock_executor):
        pkg = json.dumps({"devDependencies": {"@vitejs/plugin-lit": "^1.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "lit"
        assert result["has_lit"] is True

    def test_lit_via_dependency(self, detector, mock_executor):
        pkg = json.dumps({"dependencies": {"lit": "^3.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "lit"

    def test_react_takes_priority_over_vue(self, detector, mock_executor):
        pkg = json.dumps({
            "dependencies": {"react": "^18.0.0", "vue": "^3.0.0"},
        })
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "react"

    def test_invalid_json(self, detector, mock_executor):
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout="bad json")
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "unknown"

    def test_no_framework_deps(self, detector, mock_executor):
        pkg = json.dumps({"dependencies": {"lodash": "^4.0.0"}})
        mock_executor.exec_command.return_value = _make_command_result(exit_code=0, stdout=pkg)
        result = detector.detect_framework(project_path="/project")
        assert result["framework"] == "unknown"

    def test_different_account_alias(self, detector, mock_executor):
        from app.core.vite_project_detector import RemoteExecutor
        mock_executor.exec_command.return_value = _make_command_result(exit_code=1, stdout="")
        detector.detect_framework(account_alias="other", project_path="/project")
        RemoteExecutor.assert_called_with("other")

    def test_resolve_path_called(self, detector, mock_executor):
        mock_executor.exec_command.return_value = _make_command_result(exit_code=1, stdout="")
        detector.detect_framework(project_path="~/project")
        mock_executor.resolve_path.assert_called_once_with("~/project")


class TestViteProjectDetectorError:
    def test_is_exception(self):
        from app.core.vite_project_detector import ViteProjectDetectorError
        assert issubclass(ViteProjectDetectorError, Exception)

    def test_raise_and_catch(self):
        from app.core.vite_project_detector import ViteProjectDetectorError
        with pytest.raises(ViteProjectDetectorError, match="test error"):
            raise ViteProjectDetectorError("test error")
