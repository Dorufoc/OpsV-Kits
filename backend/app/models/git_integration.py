from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DeployStage(BaseModel):
    name: str = Field(..., description="阶段名称")
    commands: list[str] = Field(..., description="执行命令列表")
    work_dir: str = Field(..., description="工作目录")
    env_vars: dict[str, str] = Field(default_factory=dict, description="环境变量")
    timeout: int = Field(default=300, description="超时秒数")
    continue_on_error: bool = Field(default=False, description="失败是否继续")


class GitRepo(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="远程仓库路径")
    current_branch: str = Field(..., description="当前分支")
    branches: list[str] = Field(default_factory=list, description="分支列表")
    remotes: dict[str, str] = Field(default_factory=dict, description="远程仓库名→URL映射")
    repo_size: str = Field(..., description="仓库大小")
    last_commit_hash: str = Field(..., description="最近提交哈希")
    last_commit_message: str = Field(..., description="最近提交信息")
    last_commit_author: str = Field(..., description="最近提交作者")
    last_commit_time: str = Field(..., description="最近提交时间")
    is_bare: bool = Field(..., description="是否裸仓库")
    has_uncommitted_changes: bool = Field(..., description="是否有未提交变更")


class GitBranch(BaseModel):
    name: str = Field(..., description="分支名")
    is_current: bool = Field(..., description="是否当前分支")
    is_remote: bool = Field(..., description="是否远程分支")
    last_commit_hash: str = Field(..., description="最近提交哈希")
    last_commit_message: str = Field(..., description="最近提交信息")
    last_commit_time: str = Field(..., description="最近提交时间")
    upstream: Optional[str] = Field(default=None, description="上游跟踪分支")


class GitCommit(BaseModel):
    hash: str = Field(..., description="完整哈希")
    short_hash: str = Field(..., description="短哈希")
    author: str = Field(..., description="作者")
    author_email: str = Field(..., description="作者邮箱")
    date: str = Field(..., description="提交时间 ISO 格式")
    message: str = Field(..., description="提交信息")
    parent_hashes: list[str] = Field(default_factory=list, description="父提交哈希列表")
    changed_files: list[str] = Field(default_factory=list, description="变更文件列表")


class GitDiff(BaseModel):
    file_path: str = Field(..., description="文件路径")
    change_type: str = Field(..., description="变更类型: added/modified/deleted/renamed")
    old_path: Optional[str] = Field(default=None, description="重命名前的路径")
    additions: int = Field(..., description="新增行数")
    deletions: int = Field(..., description="删除行数")
    diff_content: str = Field(..., description="unified diff 内容")


class WebhookConfig(BaseModel):
    hook_id: str = Field(..., description="唯一标识")
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    platform: str = Field(..., description="平台: github/gitlab/gitee")
    secret: str = Field(..., description="签名密钥")
    events: list[str] = Field(default_factory=list, description="监听事件列表")
    branch_filter: str = Field(..., description="分支过滤")
    deploy_pipeline_id: Optional[str] = Field(default=None, description="关联的部署流程 ID")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class DeployPipeline(BaseModel):
    pipeline_id: str = Field(..., description="唯一标识")
    name: str = Field(..., description="流程名称")
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    trigger_branches: list[str] = Field(default_factory=list, description="触发分支")
    trigger_tags: str = Field(..., description="触发标签正则")
    stages: list[DeployStage] = Field(default_factory=list, description="部署阶段列表")
    auto_deploy_on_sync: bool = Field(default=False, description="定时同步后是否自动部署")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class DeployRecord(BaseModel):
    record_id: str = Field(..., description="唯一标识")
    pipeline_id: str = Field(..., description="关联流程 ID")
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    trigger_type: str = Field(..., description="触发类型: manual/webhook/sync")
    trigger_info: str = Field(..., description="触发详情")
    branch: str = Field(..., description="部署分支")
    commit_hash: str = Field(..., description="部署提交")
    status: str = Field(..., description="状态: pending/running/completed/failed/rolled_back")
    started_at: Optional[str] = Field(default=None, description="开始时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
    log: str = Field(default="", description="部署日志")
    stages_result: list[dict] = Field(default_factory=list, description="各阶段执行结果")


class GitSyncConfig(BaseModel):
    config_id: str = Field(..., description="唯一标识")
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    enabled: bool = Field(default=True, description="是否启用定时同步")
    check_interval: int = Field(default=1800, description="检查间隔秒数")
    sync_mode: str = Field(..., description="同步模式: auto_pull/notify_only/manual")
    auto_deploy: bool = Field(default=False, description="拉取后是否自动部署")
    deploy_pipeline_id: Optional[str] = Field(default=None, description="关联部署流程")
    branch: str = Field(..., description="跟踪分支")
    ff_only: bool = Field(default=True, description="是否仅快进合并")
    last_check_time: Optional[str] = Field(default=None, description="上次检查时间")
    last_sync_time: Optional[str] = Field(default=None, description="上次同步时间")
    last_sync_result: Optional[str] = Field(default=None, description="上次同步结果")
    pending_updates: int = Field(default=0, description="待拉取的提交数")
    error_count: int = Field(default=0, description="连续错误计数")
    status: str = Field(default="active", description="状态: active/paused/error")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class GitSyncLog(BaseModel):
    log_id: str = Field(..., description="唯一标识")
    config_id: str = Field(..., description="关联同步配置 ID")
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    action: str = Field(..., description="操作: fetch/pull")
    result: str = Field(..., description="结果: success/conflict/error/no_change")
    message: str = Field(..., description="详细信息")
    commits_behind: int = Field(default=0, description="落后远程的提交数")
    commits_ahead: int = Field(default=0, description="领先远程的提交数")
    changed_files: list[str] = Field(default_factory=list, description="变更文件列表")
    timestamp: str = Field(..., description="时间戳")


class GitRepoInit(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="远程仓库路径")
    gitignore_template: Optional[str] = Field(default=None, description="Gitignore 模板")


class GitRepoClone(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_url: str = Field(..., description="仓库 URL")
    target_path: str = Field(..., description="目标路径")
    branch: Optional[str] = Field(default=None, description="克隆分支")
    depth: Optional[int] = Field(default=None, description="克隆深度")


class GitRemoteConfig(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="远程仓库路径")
    remote_name: str = Field(..., description="远程仓库名称")
    remote_url: str = Field(..., description="远程仓库 URL")
    auth_type: Optional[str] = Field(default=None, description="认证类型")
    auth_credential: Optional[str] = Field(default=None, description="认证凭据")


class GitBranchCreate(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="远程仓库路径")
    branch_name: str = Field(..., description="分支名")
    base_ref: Optional[str] = Field(default=None, description="基于的引用")
    checkout: bool = Field(default=False, description="是否切换到新分支")


class GitBranchSwitch(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="远程仓库路径")
    branch_name: str = Field(..., description="分支名")
    stash_if_dirty: bool = Field(default=False, description="脏工作区是否暂存")


class GitBranchMerge(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="远程仓库路径")
    source_branch: str = Field(..., description="源分支")
    target_branch: Optional[str] = Field(default=None, description="目标分支")


class GitBranchDelete(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="远程仓库路径")
    branch_name: str = Field(..., description="分支名")
    force: bool = Field(default=False, description="是否强制删除")


class GitBranchCompare(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="远程仓库路径")
    source_branch: str = Field(..., description="源分支")
    target_branch: str = Field(..., description="目标分支")


class GitLogFilter(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="远程仓库路径")
    author: Optional[str] = Field(default=None, description="作者过滤")
    since: Optional[str] = Field(default=None, description="起始时间")
    until: Optional[str] = Field(default=None, description="结束时间")
    keyword: Optional[str] = Field(default=None, description="关键词过滤")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=20, description="每页数量")


class WebhookConfigCreate(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    platform: str = Field(..., description="平台: github/gitlab/gitee")
    events: list[str] = Field(default_factory=list, description="监听事件列表")
    branch_filter: str = Field(..., description="分支过滤")
    deploy_pipeline_id: Optional[str] = Field(default=None, description="关联的部署流程 ID")


class DeployPipelineCreate(BaseModel):
    name: str = Field(..., description="流程名称")
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    trigger_branches: list[str] = Field(default_factory=list, description="触发分支")
    trigger_tags: str = Field(..., description="触发标签正则")
    stages: list[DeployStage] = Field(default_factory=list, description="部署阶段列表")
    auto_deploy_on_sync: bool = Field(default=False, description="定时同步后是否自动部署")


class GitSyncConfigCreate(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    enabled: bool = Field(default=True, description="是否启用定时同步")
    check_interval: int = Field(default=1800, description="检查间隔秒数")
    sync_mode: str = Field(..., description="同步模式: auto_pull/notify_only/manual")
    auto_deploy: bool = Field(default=False, description="拉取后是否自动部署")
    deploy_pipeline_id: Optional[str] = Field(default=None, description="关联部署流程")
    branch: str = Field(..., description="跟踪分支")
    ff_only: bool = Field(default=True, description="是否仅快进合并")


class GitSyncConfigUpdate(BaseModel):
    enabled: Optional[bool] = Field(default=None, description="是否启用定时同步")
    check_interval: Optional[int] = Field(default=None, description="检查间隔秒数")
    sync_mode: Optional[str] = Field(default=None, description="同步模式: auto_pull/notify_only/manual")
    auto_deploy: Optional[bool] = Field(default=None, description="拉取后是否自动部署")
    deploy_pipeline_id: Optional[str] = Field(default=None, description="关联部署流程")
    branch: Optional[str] = Field(default=None, description="跟踪分支")
    ff_only: Optional[bool] = Field(default=None, description="是否仅快进合并")
