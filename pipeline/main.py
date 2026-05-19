"""
ESL Content Pipeline — Orchestrator
Runs all five steps in sequence and saves JSON artifacts for each step.
Invoked daily by GitHub Actions (.github/workflows/content-pipeline.yml).
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path


# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("pipeline.main")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save(name: str, data) -> None:
    out = Path("pipeline/output")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(data, indent=2, default=str))


def _banner(text: str) -> None:
    logger.info("─" * 60)
    logger.info(f"  {text}")
    logger.info("─" * 60)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    started_at = datetime.utcnow()
    _banner(f"ESL Content Pipeline  |  {started_at.strftime('%Y-%m-%d %H:%M UTC')}")

    # Step 1 — Market Research
    _banner("Step 1 / 5 — Market Research")
    from pipeline.research import run_research
    research = run_research()
    _save("01_research", research)

    # Step 2 — Topic Selection & Content Generation
    _banner("Step 2 / 5 — Topic Selection & Content Generation")
    from pipeline.topic_selector import select_topic
    content_plan = select_topic(research)
    _save("02_content_plan", content_plan)
    logger.info(f"Topic chosen: '{content_plan['topic']}'")

    # Step 3 — Carousel Creation (Canva)
    _banner("Step 3 / 5 — Carousel Creation (Canva)")
    from pipeline.carousel_creator import create_carousel
    local_slides = create_carousel(content_plan["carousel"])
    _save("03_local_slides", local_slides)
    logger.info(f"{len(local_slides)} slides saved locally")

    # Step 4 — Upload to Supabase Storage
    _banner("Step 4 / 5 — Upload to Supabase Storage")
    from pipeline.supabase_uploader import upload_slides
    public_urls = upload_slides(local_slides)
    _save("04_public_urls", public_urls)

    # Step 5 — Post to Instagram
    _banner("Step 5 / 5 — Post to Instagram")
    from pipeline.instagram_poster import post_carousel
    post_id = post_carousel(public_urls, content_plan["caption"])

    # Summary
    elapsed = (datetime.utcnow() - started_at).seconds
    summary = {
        "status": "success",
        "post_id": post_id,
        "topic": content_plan["topic"],
        "pillar": content_plan["pillar"],
        "slides": len(local_slides),
        "elapsed_seconds": elapsed,
        "timestamp": started_at.isoformat(),
    }
    _save("05_summary", summary)

    _banner(f"Done in {elapsed}s  |  Post ID: {post_id}  |  Topic: {content_plan['topic']}")


if __name__ == "__main__":
    main()
