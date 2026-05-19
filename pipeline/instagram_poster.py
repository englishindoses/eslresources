"""
Step 5 — Instagram Posting
Posts the carousel to an Instagram Business/Creator account using the
Instagram Graph API.

Requirements:
  • Instagram Business or Creator account
  • Facebook Page connected to the IG account
  • A Meta app with instagram_basic + instagram_content_publish permissions
  • A long-lived User Access Token (valid ~60 days; refresh before expiry)

Add as GitHub Secrets:
  INSTAGRAM_ACCOUNT_ID   — numeric IG User ID (not the @handle)
  INSTAGRAM_ACCESS_TOKEN — long-lived access token
"""
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.facebook.com/v20.0"


def _post(endpoint: str, data: dict) -> dict:
    resp = requests.post(f"{_GRAPH_BASE}/{endpoint}", data=data, timeout=30)
    payload = resp.json()
    if "error" in payload:
        raise RuntimeError(
            f"Instagram API error on /{endpoint}: {payload['error']['message']}"
        )
    return payload


def _wait_for_container(container_id: str, token: str, timeout: int = 90) -> None:
    """Polls until the media container reaches FINISHED status."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(
            f"{_GRAPH_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=15,
        )
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Media container {container_id} entered ERROR state")
        time.sleep(5)
    raise TimeoutError(f"Container {container_id} not ready after {timeout}s")


def post_carousel(image_urls: list[str], caption: str) -> str:
    """
    Publishes a carousel post to Instagram.
    Returns the published post ID.
    """
    if not (2 <= len(image_urls) <= 10):
        raise ValueError(
            f"Instagram carousels need 2–10 images; got {len(image_urls)}"
        )

    account_id = os.environ["INSTAGRAM_ACCOUNT_ID"]
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"]

    # ── 1. Create a media container for each slide ────────────────────────────
    logger.info(f"Creating {len(image_urls)} media containers…")
    child_ids: list[str] = []

    for i, url in enumerate(image_urls, start=1):
        result = _post(
            f"{account_id}/media",
            {
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": token,
            },
        )
        container_id = result["id"]
        logger.info(f"  Slide {i}: container {container_id} — waiting for FINISHED…")
        _wait_for_container(container_id, token)
        child_ids.append(container_id)

    # ── 2. Create the carousel container ─────────────────────────────────────
    logger.info("Creating carousel container…")
    carousel = _post(
        f"{account_id}/media",
        {
            "media_type": "CAROUSEL",
            "caption": caption,
            "children": ",".join(child_ids),
            "access_token": token,
        },
    )
    carousel_id = carousel["id"]
    logger.info(f"Carousel container {carousel_id} — waiting for FINISHED…")
    _wait_for_container(carousel_id, token, timeout=120)

    # ── 3. Publish ────────────────────────────────────────────────────────────
    logger.info("Publishing carousel…")
    result = _post(
        f"{account_id}/media_publish",
        {"creation_id": carousel_id, "access_token": token},
    )
    post_id = result["id"]
    logger.info(f"Published successfully! Post ID: {post_id}")
    return post_id
