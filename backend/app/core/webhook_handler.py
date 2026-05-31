from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WebhookVerificationError(Exception):
    pass


class WebhookEvent:
    def __init__(
        self,
        platform: str,
        event_type: str,
        branch: Optional[str],
        tag: Optional[str],
        commits: list[dict],
        pusher: Optional[str],
        repository: Optional[str],
        raw_body: bytes,
    ):
        self.platform = platform
        self.event_type = event_type
        self.branch = branch
        self.tag = tag
        self.commits = commits
        self.pusher = pusher
        self.repository = repository
        self.raw_body = raw_body

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "event_type": self.event_type,
            "branch": self.branch,
            "tag": self.tag,
            "commits": self.commits,
            "pusher": self.pusher,
            "repository": self.repository,
        }


def verify_github_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_gitlab_signature(body: bytes, token: str, secret: str) -> bool:
    return hmac.compare_digest(token, secret)


def verify_gitee_signature(body: bytes, password: str, secret: str) -> bool:
    return hmac.compare_digest(password, secret)


def verify_webhook(platform: str, body: bytes, headers: dict[str, str], secret: str) -> bool:
    if platform == "github":
        signature = headers.get("X-Hub-Signature-256", "")
        if not signature:
            raise WebhookVerificationError("Missing X-Hub-Signature-256 header")
        if not verify_github_signature(body, signature, secret):
            raise WebhookVerificationError("GitHub webhook signature verification failed")
        return True
    elif platform == "gitlab":
        token = headers.get("X-Gitlab-Token", "")
        if not token:
            raise WebhookVerificationError("Missing X-Gitlab-Token header")
        if not verify_gitlab_signature(body, token, secret):
            raise WebhookVerificationError("GitLab webhook token verification failed")
        return True
    elif platform == "gitee":
        password = headers.get("X-Gitee-Password", "")
        if not password:
            raise WebhookVerificationError("Missing X-Gitee-Password header")
        if not verify_gitee_signature(body, password, secret):
            raise WebhookVerificationError("Gitee webhook password verification failed")
        return True
    else:
        raise WebhookVerificationError(f"Unsupported platform: {platform}")


def _extract_ref(ref: str) -> tuple[Optional[str], Optional[str]]:
    if ref.startswith("refs/heads/"):
        return ref[len("refs/heads/"):], None
    elif ref.startswith("refs/tags/"):
        return None, ref[len("refs/tags/"):]
    return None, None


def parse_github_event(body: bytes, headers: dict[str, str]) -> WebhookEvent:
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise WebhookVerificationError(f"Invalid JSON body: {e}")

    event_type = headers.get("X-GitHub-Event", "unknown")
    branch: Optional[str] = None
    tag: Optional[str] = None
    commits: list[dict] = []
    pusher: Optional[str] = None
    repository: Optional[str] = None

    repo_info = data.get("repository")
    if repo_info:
        repository = repo_info.get("full_name")

    if event_type == "push":
        ref = data.get("ref", "")
        branch, tag = _extract_ref(ref)
        commits = data.get("commits", [])
        pusher_info = data.get("pusher")
        if pusher_info:
            pusher = pusher_info.get("name")
    elif event_type == "pull_request":
        pr = data.get("pull_request", {})
        action = data.get("action", "")
        event_type = f"pull_request.{action}"
        branch = pr.get("base", {}).get("ref")
        pusher = pr.get("user", {}).get("login")
    else:
        pusher_info = data.get("sender")
        if pusher_info:
            pusher = pusher_info.get("login")

    return WebhookEvent(
        platform="github",
        event_type=event_type,
        branch=branch,
        tag=tag,
        commits=commits,
        pusher=pusher,
        repository=repository,
        raw_body=body,
    )


def parse_gitlab_event(body: bytes, headers: dict[str, str]) -> WebhookEvent:
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise WebhookVerificationError(f"Invalid JSON body: {e}")

    event_type = headers.get("X-Gitlab-Event", "unknown")
    branch: Optional[str] = None
    tag: Optional[str] = None
    commits: list[dict] = []
    pusher: Optional[str] = None
    repository: Optional[str] = None

    repo_info = data.get("project")
    if repo_info:
        repository = repo_info.get("path_with_namespace")

    if event_type == "Push Hook":
        ref = data.get("ref", "")
        branch, tag = _extract_ref(ref)
        commits = data.get("commits", [])
        pusher = data.get("user_name")
    elif event_type == "Merge Request Hook":
        mr = data.get("object_attributes", {})
        action = mr.get("action", "")
        event_type = f"merge_request.{action}"
        branch = mr.get("target_branch")
        pusher = data.get("user", {}).get("name")
    else:
        pusher = data.get("user_name")

    return WebhookEvent(
        platform="gitlab",
        event_type=event_type,
        branch=branch,
        tag=tag,
        commits=commits,
        pusher=pusher,
        repository=repository,
        raw_body=body,
    )


def parse_gitee_event(body: bytes, headers: dict[str, str]) -> WebhookEvent:
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise WebhookVerificationError(f"Invalid JSON body: {e}")

    event_type = headers.get("X-Gitee-Event", "unknown")
    branch: Optional[str] = None
    tag: Optional[str] = None
    commits: list[dict] = []
    pusher: Optional[str] = None
    repository: Optional[str] = None

    repo_info = data.get("repository")
    if repo_info:
        repository = repo_info.get("full_name") or repo_info.get("path_with_namespace")

    if event_type == "Push Hook":
        ref = data.get("ref", "")
        branch, tag = _extract_ref(ref)
        commits = data.get("commits", [])
        pusher = data.get("user_name")
    elif event_type == "Merge Request Hook":
        mr = data.get("merge_request", data.get("object_attributes", {}))
        action = mr.get("action", data.get("action", ""))
        event_type = f"merge_request.{action}"
        branch = mr.get("target_branch")
        pusher = data.get("user", {}).get("name") or data.get("user_name")
    else:
        pusher = data.get("user_name")

    return WebhookEvent(
        platform="gitee",
        event_type=event_type,
        branch=branch,
        tag=tag,
        commits=commits,
        pusher=pusher,
        repository=repository,
        raw_body=body,
    )


def parse_webhook_event(platform: str, body: bytes, headers: dict[str, str]) -> WebhookEvent:
    if platform == "github":
        return parse_github_event(body, headers)
    elif platform == "gitlab":
        return parse_gitlab_event(body, headers)
    elif platform == "gitee":
        return parse_gitee_event(body, headers)
    else:
        raise WebhookVerificationError(f"Unsupported platform: {platform}")
