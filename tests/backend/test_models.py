"""数据模型测试"""
import pytest
from pydantic import ValidationError
from app.models.ssh_account import SSHAccount, SSHAccountCreate, SSHAccountUpdate, AccountGroup, AccountGroupCreate
from app.models.project_config import ProjectConfig, ProjectConfigCreate, ProjectConfigUpdate
from app.models.build_task import BuildTask


class TestSSHAccountModel:
    """SSH账户模型测试"""

    def test_ssh_account_create_valid(self):
        account = SSHAccount(
            alias="test-server",
            host="192.168.1.100",
            port=22,
            username="testuser",
            auth_type="password",
        )
        assert account.alias == "test-server"
        assert account.port == 22
        assert account.auth_type == "password"
        assert account.password is None

    def test_ssh_account_create_with_password(self):
        account = SSHAccount(
            alias="test-server",
            host="192.168.1.100",
            port=2222,
            username="testuser",
            auth_type="password",
            password="encrypted-pass",
        )
        assert account.port == 2222
        assert account.password == "encrypted-pass"

    def test_ssh_account_create_with_key(self):
        account = SSHAccount(
            alias="test-server",
            host="192.168.1.100",
            username="testuser",
            auth_type="key",
            private_key="/path/to/key",
        )
        assert account.auth_type == "key"
        assert account.private_key == "/path/to/key"

    def test_ssh_account_create_missing_fields(self):
        with pytest.raises(ValidationError):
            SSHAccount()

    def test_ssh_account_create_invalid_port(self):
        with pytest.raises(ValidationError):
            SSHAccount(alias="test", host="192.168.1.1", username="user", port="invalid")

    def test_ssh_account_create_with_group(self):
        account = SSHAccount(
            alias="test-server",
            host="192.168.1.100",
            username="testuser",
            group="production",
            workplace_path="/opt/projects",
        )
        assert account.group == "production"
        assert account.workplace_path == "/opt/projects"


class TestSSHAccountCreateModel:
    """SSH账户创建模型测试"""

    def test_ssh_account_create_model_valid(self):
        create = SSHAccountCreate(
            alias="new-server",
            host="192.168.1.200",
            port=22,
            username="admin",
            auth_type="password",
            password="secret123",
        )
        assert create.alias == "new-server"
        assert create.password == "secret123"

    def test_ssh_account_create_model_defaults(self):
        create = SSHAccountCreate(
            alias="new-server",
            host="192.168.1.200",
            username="admin",
        )
        assert create.port == 22
        assert create.auth_type == "password"
        assert create.is_default is False
        assert create.group is None


class TestSSHAccountUpdateModel:
    """SSH账户更新模型测试"""

    def test_ssh_account_update_partial(self):
        update = SSHAccountUpdate(host="192.168.1.200", port=2222)
        assert update.host == "192.168.1.200"
        assert update.port == 2222
        assert update.username is None

    def test_ssh_account_update_all_fields(self):
        update = SSHAccountUpdate(
            host="192.168.1.200",
            port=2222,
            username="newuser",
            auth_type="key",
            private_key="/new/path",
            group="development",
        )
        assert update.host == "192.168.1.200"
        assert update.group == "development"


class TestAccountGroupModel:
    """账户分组模型测试"""

    def test_account_group_create(self):
        group = AccountGroupCreate(
            name="production",
            accounts=["server1", "server2", "server3"],
        )
        assert group.name == "production"
        assert len(group.accounts) == 3

    def test_account_group_empty(self):
        group = AccountGroupCreate(name="empty-group")
        assert group.name == "empty-group"
        assert group.accounts == []

    def test_account_group_model(self):
        group = AccountGroup(
            name="production",
            accounts=["server1", "server2"],
        )
        assert group.name == "production"
        assert len(group.accounts) == 2


class TestProjectConfigModel:
    """项目配置模型测试"""

    def test_project_config_create(self):
        project = ProjectConfigCreate(
            alias="my-project",
            local_path="/home/user/project",
            remote_path="/opt/project",
            ssh_alias="test-server",
            jdk_version="21",
        )
        assert project.alias == "my-project"
        assert project.jdk_version == "21"

    def test_project_config_create_defaults(self):
        project = ProjectConfigCreate(alias="minimal")
        assert project.local_path == ""
        assert project.remote_path == ""
        assert project.ssh_alias == ""
        assert project.jdk_version == "21"

    def test_project_config_update(self):
        update = ProjectConfigUpdate(
            local_path="/new/path",
            jdk_version="17",
        )
        assert update.local_path == "/new/path"
        assert update.remote_path is None
        assert update.ssh_alias is None

    def test_project_config_model(self):
        config = ProjectConfig(
            alias="my-project",
            local_path="/path",
            remote_path="/remote",
            ssh_alias="server",
        )
        assert config.alias == "my-project"
        assert "created_at" in config.model_dump()
        assert "updated_at" in config.model_dump()


class TestBuildTaskModel:
    """构建任务模型测试"""

    def test_build_task_to_dict(self):
        task = BuildTask(
            task_id="task-123",
            account_alias="test-server",
            project_path="/opt/project",
            action="compile",
        )
        result = task.to_dict()
        assert result["task_id"] == "task-123"
        assert result["action"] == "compile"
        assert result["status"] == "pending"

    def test_build_task_status_updates(self):
        task = BuildTask(
            task_id="task-456",
            account_alias="test-server",
            project_path="/opt/project",
            action="package",
        )
        task.status = "running"
        task.append_log("Building...\n")
        result = task.to_dict()
        assert result["status"] == "running"
        assert "Building" in result["log"]
