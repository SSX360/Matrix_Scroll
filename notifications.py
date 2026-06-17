"""Slack notifier for the Matrix Scroll dev team.

Routes logical events to channels in the workspace. Two transports are supported,
checked per-channel in this order:

  1. Incoming webhook  -> SLACK_WEBHOOK_<KEY>   (post-only, one URL per channel)
  2. Bot token         -> SLACK_BOT_TOKEN        (chat.postMessage to any channel)

The module is INERT when nothing is configured: notify() returns False and never
raises, so local runs and CI without secrets are unaffected.

Secret hygiene: tokens and webhook URLs are never logged. Logs name the channel
only (e.g. "posted to #feed-ci-cd-qa"). Configure values in .env (gitignored).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests

POST_TIMEOUT_S = 6.0
_API_URL = "https://slack.com/api/chat.postMessage"

# Logical event key -> (channel env var, default channel, webhook env var).
_ROUTES: dict[str, tuple[str, str, str]] = {
    "cicd": ("SLACK_CHANNEL_CICD", "#feed-ci-cd-qa", "SLACK_WEBHOOK_CICD"),
    "checkout": ("SLACK_CHANNEL_CHECKOUT", "#feed-web3-checkout", "SLACK_WEBHOOK_CHECKOUT"),
    "announce": ("SLACK_CHANNEL_ANNOUNCE", "#00-announcements", "SLACK_WEBHOOK_ANNOUNCE"),
}


def _log(msg: str) -> None:
    # stderr only: MCP stdio transport owns stdout.
    print(f"[notify] {msg}", file=sys.stderr)


def _bot_token() -> str:
    return os.environ.get("SLACK_BOT_TOKEN", "").strip()


def _webhook_for(event_key: str) -> str:
    route = _ROUTES.get(event_key)
    if not route:
        return ""
    return os.environ.get(route[2], "").strip()


def _channel_for(event_key: str) -> str:
    route = _ROUTES.get(event_key)
    if not route:
        return ""
    return os.environ.get(route[0], route[1]).strip()


def enabled(event_key: str | None = None) -> bool:
    """True if a transport is configured (optionally for a specific event)."""
    if _bot_token():
        return True
    if event_key is not None:
        return bool(_webhook_for(event_key))
    return any(os.environ.get(r[2], "").strip() for r in _ROUTES.values())


def _post_webhook(url: str, payload: dict[str, Any]) -> bool:
    resp = requests.post(url, json=payload, timeout=POST_TIMEOUT_S)
    return resp.ok


def _post_bot(channel: str, payload: dict[str, Any]) -> bool:
    body = dict(payload)
    body["channel"] = channel
    resp = requests.post(
        _API_URL,
        json=body,
        headers={"Authorization": f"Bearer {_bot_token()}"},
        timeout=POST_TIMEOUT_S,
    )
    if not resp.ok:
        return False
    try:
        return bool(resp.json().get("ok"))
    except (ValueError, json.JSONDecodeError):
        return False


def notify(
    event_key: str,
    text: str,
    *,
    blocks: list[dict[str, Any]] | None = None,
) -> bool:
    """Post text (and optional Block Kit blocks) to the channel for event_key.

    Returns True on a confirmed post, False if inert or on any failure. Never
    raises; failures are logged by channel name only.
    """
    channel = _channel_for(event_key)
    label = channel or f"<{event_key}>"
    payload: dict[str, Any] = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    webhook = _webhook_for(event_key)
    try:
        if webhook:
            ok = _post_webhook(webhook, payload)
        elif _bot_token() and channel:
            ok = _post_bot(channel, payload)
        else:
            return False
    except requests.RequestException as exc:
        _log(f"post to {label} failed: {type(exc).__name__}")
        return False

    if ok:
        _log(f"posted to {label}")
    else:
        _log(f"post to {label} rejected by Slack")
    return ok
