import os
import unittest
from unittest import mock

import requests

import notifications
from qa import release_evidence


class FakeResp:
    def __init__(self, ok=True, payload=None):
        self.ok = ok
        self._payload = payload if payload is not None else {"ok": True}

    def json(self):
        return self._payload


def _env(**overrides):
    """Deterministic Slack env: everything off unless overridden."""
    base = {
        "SLACK_BOT_TOKEN": "",
        "SLACK_WEBHOOK_CICD": "",
        "SLACK_WEBHOOK_CHECKOUT": "",
        "SLACK_WEBHOOK_ANNOUNCE": "",
        "SLACK_CHANNEL_CICD": "#feed-ci-cd-qa",
        "SLACK_CHANNEL_CHECKOUT": "#feed-web3-checkout",
        "SLACK_CHANNEL_ANNOUNCE": "#00-announcements",
    }
    base.update(overrides)
    return mock.patch.dict(os.environ, base, clear=False)


class NotifierTransportTests(unittest.TestCase):
    def test_inert_when_unconfigured(self):
        with _env(), mock.patch("notifications.requests.post") as post:
            self.assertFalse(notifications.enabled())
            self.assertFalse(notifications.enabled("cicd"))
            self.assertFalse(notifications.notify("cicd", "hello"))
            post.assert_not_called()

    def test_bot_token_posts_to_chat_api(self):
        with _env(SLACK_BOT_TOKEN="xoxb-test"), \
                mock.patch("notifications.requests.post", return_value=FakeResp()) as post:
            self.assertTrue(notifications.enabled("cicd"))
            self.assertTrue(notifications.notify("cicd", "gates pass"))
            post.assert_called_once()
            args, kwargs = post.call_args
            self.assertEqual(args[0], "https://slack.com/api/chat.postMessage")
            self.assertEqual(kwargs["headers"]["Authorization"], "Bearer xoxb-test")
            self.assertEqual(kwargs["json"]["channel"], "#feed-ci-cd-qa")
            self.assertEqual(kwargs["json"]["text"], "gates pass")

    def test_webhook_takes_precedence_over_bot(self):
        hook = "https://hooks.slack.test/abc"
        with _env(SLACK_BOT_TOKEN="xoxb-test", SLACK_WEBHOOK_CICD=hook), \
                mock.patch("notifications.requests.post", return_value=FakeResp()) as post:
            self.assertTrue(notifications.notify("cicd", "via hook"))
            args, kwargs = post.call_args
            self.assertEqual(args[0], hook)
            self.assertNotIn("headers", kwargs)
            self.assertEqual(kwargs["json"]["text"], "via hook")

    def test_checkout_routes_to_checkout_channel(self):
        with _env(SLACK_BOT_TOKEN="xoxb-test"), \
                mock.patch("notifications.requests.post", return_value=FakeResp()) as post:
            self.assertTrue(notifications.notify("checkout", "new order"))
            self.assertEqual(post.call_args.kwargs["json"]["channel"], "#feed-web3-checkout")

    def test_slack_rejection_returns_false(self):
        with _env(SLACK_BOT_TOKEN="xoxb-test"), \
                mock.patch("notifications.requests.post",
                           return_value=FakeResp(payload={"ok": False})):
            self.assertFalse(notifications.notify("cicd", "x"))

    def test_request_exception_is_swallowed(self):
        with _env(SLACK_BOT_TOKEN="xoxb-test"), \
                mock.patch("notifications.requests.post",
                           side_effect=requests.RequestException("boom")):
            self.assertFalse(notifications.notify("cicd", "x"))

    def test_enabled_webhook_only_is_channel_specific(self):
        with _env(SLACK_WEBHOOK_CICD="https://hooks.slack.test/x"):
            self.assertTrue(notifications.enabled("cicd"))
            self.assertFalse(notifications.enabled("announce"))


class ReleaseAnnounceTests(unittest.TestCase):
    def _manifest(self, *, sw=True, tag=None, signed=True):
        return {
            "run_id": "rel-1",
            "release_decision": {"software_release_candidate": sw, "device_gtm_ready": False},
            "signature": {"value": "sig", "device_id": "MS-TEST"} if signed else {},
            "git": {"tag": tag},
        }

    def test_tagged_candidate_posts_cicd_and_announce(self):
        with mock.patch.object(release_evidence, "notifications") as mn:
            mn.enabled.return_value = True
            release_evidence._notify_release(self._manifest(sw=True, tag="v1.0.0"))
        keys = [c.args[0] for c in mn.notify.call_args_list]
        self.assertEqual(keys, ["cicd", "announce"])

    def test_untagged_candidate_skips_announce(self):
        with mock.patch.object(release_evidence, "notifications") as mn:
            mn.enabled.return_value = True
            release_evidence._notify_release(self._manifest(sw=True, tag=None))
        keys = [c.args[0] for c in mn.notify.call_args_list]
        self.assertEqual(keys, ["cicd"])

    def test_failed_candidate_skips_announce_even_if_tagged(self):
        with mock.patch.object(release_evidence, "notifications") as mn:
            mn.enabled.return_value = True
            release_evidence._notify_release(self._manifest(sw=False, tag="v1.0.0"))
        keys = [c.args[0] for c in mn.notify.call_args_list]
        self.assertEqual(keys, ["cicd"])

    def test_unsigned_manifest_reports_unsigned_signer(self):
        with mock.patch.object(release_evidence, "notifications") as mn:
            mn.enabled.return_value = True
            release_evidence._notify_release(self._manifest(sw=True, tag=None, signed=False))
        self.assertIn("unsigned", mn.notify.call_args_list[0].args[1])


if __name__ == "__main__":
    unittest.main()
