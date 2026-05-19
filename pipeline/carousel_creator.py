"""
Step 3 — Carousel Creation
Autofills a Canva brand template with today's content, exports each slide
as a PNG, and saves them locally under pipeline/output/slides/.

Canva Connect API docs:
  https://www.canva.com/developers/docs/connect/
"""
import logging
import os
import time
from pathlib import Path

import requests
import yaml

logger = logging.getLogger(__name__)

_CANVA_BASE = "https://api.canva.com/rest/v1"


def _auth_headers() -> dict:
    token = os.environ["CANVA_API_TOKEN"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _poll_job(url: str, interval: int = 3, timeout: int = 120) -> dict:
    """Poll a Canva job URL until status is 'success' or raises."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(url, headers=_auth_headers(), timeout=15)
        resp.raise_for_status()
        job = resp.json().get("job", {})
        status = job.get("status")
        if status == "success":
            return job
        if status == "failed":
            raise RuntimeError(f"Canva job failed: {job}")
        time.sleep(interval)
    raise TimeoutError(f"Canva job at {url} timed out after {timeout}s")


def _load_template_id() -> str:
    # Prefer the GitHub Secret; fall back to brand_config.yml
    template_id = os.environ.get("CANVA_BRAND_TEMPLATE_ID", "")
    if not template_id:
        config = yaml.safe_load(
            (Path(__file__).parent / "brand_config.yml").read_text()
        )
        template_id = config["canva"]["brand_template_id"]
    if not template_id or template_id == "YOUR_CANVA_BRAND_TEMPLATE_ID":
        raise ValueError(
            "Canva brand template ID is not set. "
            "Add CANVA_BRAND_TEMPLATE_ID as a GitHub Secret or update brand_config.yml."
        )
    return template_id


def _build_autofill_data(carousel_content: dict, field_map: dict) -> dict:
    """
    Converts carousel content keys → Canva autofill format.
    field_map: {content_key: canva_field_name}
    """
    data = {}
    for content_key, canva_field in field_map.items():
        text = carousel_content.get(content_key, "").strip()
        if text:
            data[canva_field] = {"type": "text", "text": text}
    return data


def create_carousel(carousel_content: dict) -> list[str]:
    """
    Creates a Canva design from the brand template, exports it as PNGs,
    downloads each slide, and returns a list of local file paths.
    """
    config = yaml.safe_load(
        (Path(__file__).parent / "brand_config.yml").read_text()
    )["canva"]

    template_id = _load_template_id()
    field_map = config["autofill_fields"]
    autofill_data = _build_autofill_data(carousel_content, field_map)

    date_str = time.strftime("%Y-%m-%d")

    # ── 1. Autofill ───────────────────────────────────────────────────────────
    logger.info(f"Starting Canva autofill (template: {template_id})…")
    resp = requests.post(
        f"{_CANVA_BASE}/autofills",
        headers=_auth_headers(),
        json={
            "brand_template_id": template_id,
            "title": f"ESL Post {date_str}",
            "data": autofill_data,
        },
        timeout=20,
    )
    resp.raise_for_status()
    autofill_job_id = resp.json()["job"]["id"]

    autofill_job = _poll_job(f"{_CANVA_BASE}/autofills/{autofill_job_id}", timeout=120)
    design_id = autofill_job["result"]["design"]["id"]
    logger.info(f"Canva design created: {design_id}")

    # ── 2. Export as PNG ──────────────────────────────────────────────────────
    logger.info("Requesting PNG export…")
    resp = requests.post(
        f"{_CANVA_BASE}/exports",
        headers=_auth_headers(),
        json={"design_id": design_id, "format": "png", "export_quality": "regular"},
        timeout=20,
    )
    resp.raise_for_status()
    export_job_id = resp.json()["job"]["id"]

    export_job = _poll_job(f"{_CANVA_BASE}/exports/{export_job_id}", timeout=180)
    export_urls: list[str] = export_job["result"]["urls"]
    logger.info(f"Export ready — {len(export_urls)} slides")

    # ── 3. Download slides locally ────────────────────────────────────────────
    out_dir = Path("pipeline/output/slides")
    out_dir.mkdir(parents=True, exist_ok=True)

    local_paths: list[str] = []
    for i, url in enumerate(export_urls, start=1):
        path = out_dir / f"slide_{i:02d}.png"
        img_bytes = requests.get(url, timeout=30).content
        path.write_bytes(img_bytes)
        local_paths.append(str(path))
        logger.info(f"  Saved slide {i} → {path}")

    return local_paths
