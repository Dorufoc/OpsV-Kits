import json
from unittest.mock import patch

import pytest

from app.core.webhook_handler import (
    WebhookEvent,
    WebhookVerificationError,
    _extract_ref,
    parse_github_event,
    parse_gitee_event,
    parse_gitlab_event,
    parse_webhook_event,
    verify_webhook,
)


class TestWebhookEventToDict:
    def test_to_dict(self):
        event = WebhookEvent(
            platform="github",
            event_type="push",
            branch="main",
            tag=None,
            commits=[{"id": "abc"}],
            pusher="user",
            repository="org/repo",
            raw_body=b"{}",
        )
        d = event.to_dict()
        assert d["platform"] == "github"
        assert d["event_type"] == "push"
        assert d["branch"] == "main"
        assert d["tag"] is None
        assert d["commits"] == [{"id": "abc"}]
        assert d["pusher"] == "user"
        assert d["repository"] == "org/repo"


class TestVerifyWebhookSignatureFailures:
    def test_github_signature_mismatch(self):
        body = b'{"ref":"refs/heads/main"}'
        with pytest.raises(WebhookVerificationError, match="GitHub webhook signature verification failed"):
            verify_webhook("github", body, {"X-Hub-Signature-256": "sha256=wrong"}, "secret")

    def test_gitlab_token_mismatch(self):
        body = b'{"ref":"refs/heads/main"}'
        with pytest.raises(WebhookVerificationError, match="GitLab webhook token verification failed"):
            verify_webhook("gitlab", body, {"X-Gitlab-Token": "wrong-token"}, "correct-secret")

    def test_gitee_password_mismatch(self):
        body = b'{"ref":"refs/heads/main"}'
        with pytest.raises(WebhookVerificationError, match="Gitee webhook password verification failed"):
            verify_webhook("gitee", body, {"X-Gitee-Password": "wrong-pass"}, "correct-pass")


class TestExtractRefNonMatching:
    def test_non_matching_ref(self):
        branch, tag = _extract_ref("refs/something/else")
        assert branch is None
        assert tag is None


class TestParseGithubEventElseBranch:
    def test_other_event_type_sender(self):
        body = json.dumps({
            "sender": {"login": "bot"},
            "repository": {"full_name": "org/repo"},
        }).encode()
        headers = {"X-GitHub-Event": "issues"}
        event = parse_github_event(body, headers)
        assert event.pusher == "bot"
        assert event.event_type == "issues"

    def test_other_event_type_no_sender(self):
        body = json.dumps({"repository": {"full_name": "org/repo"}}).encode()
        headers = {"X-GitHub-Event": "release"}
        event = parse_github_event(body, headers)
        assert event.pusher is None


class TestParseGitlabEventJsonError:
    def test_invalid_json(self):
        body = b"not valid json{"
        headers = {"X-Gitlab-Event": "Push Hook"}
        with pytest.raises(WebhookVerificationError, match="Invalid JSON body"):
            parse_gitlab_event(body, headers)


class TestParseGitlabEventElseBranch:
    def test_other_event_type(self):
        body = json.dumps({
            "user_name": "dev",
            "project": {"path_with_namespace": "org/repo"},
        }).encode()
        headers = {"X-Gitlab-Event": "Tag Push Hook"}
        event = parse_gitlab_event(body, headers)
        assert event.pusher == "dev"
        assert event.event_type == "Tag Push Hook"


class TestParseGiteeEventJsonError:
    def test_invalid_json(self):
        body = b"broken json"
        headers = {"X-Gitee-Event": "Push Hook"}
        with pytest.raises(WebhookVerificationError, match="Invalid JSON body"):
            parse_gitee_event(body, headers)


class TestParseGiteeEventElseBranch:
    def test_other_event_type(self):
        body = json.dumps({
            "user_name": "dev",
            "repository": {"full_name": "org/repo"},
        }).encode()
        headers = {"X-Gitee-Event": "Note Hook"}
        event = parse_gitee_event(body, headers)
        assert event.pusher == "dev"
        assert event.event_type == "Note Hook"


class TestParseWebhookEventDispatch:
    def test_github_dispatch(self):
        body = json.dumps({
            "ref": "refs/heads/main",
            "commits": [],
            "pusher": {"name": "user"},
            "repository": {"full_name": "org/repo"},
        }).encode()
        headers = {"X-GitHub-Event": "push"}
        event = parse_webhook_event("github", body, headers)
        assert event.platform == "github"
        assert event.branch == "main"

    def test_gitlab_dispatch(self):
        body = json.dumps({
            "ref": "refs/heads/main",
            "commits": [],
            "user_name": "dev",
            "project": {"path_with_namespace": "org/repo"},
        }).encode()
        headers = {"X-Gitlab-Event": "Push Hook"}
        event = parse_webhook_event("gitlab", body, headers)
        assert event.platform == "gitlab"

    def test_gitee_dispatch(self):
        body = json.dumps({
            "ref": "refs/heads/main",
            "commits": [],
            "user_name": "dev",
            "repository": {"full_name": "org/repo"},
        }).encode()
        headers = {"X-Gitee-Event": "Push Hook"}
        event = parse_webhook_event("gitee", body, headers)
        assert event.platform == "gitee"

    def test_unsupported_platform(self):
        with pytest.raises(WebhookVerificationError, match="Unsupported platform"):
            parse_webhook_event("bitbucket", b"{}", {})
