"""
Step 2 — Topic Selection & Content Generation
Uses Claude to analyse the research signals, choose the best topic for
today's post, and produce carousel-ready copy.
"""
import json
import logging
import os
from pathlib import Path

import anthropic
import yaml

logger = logging.getLogger(__name__)


def _load_brand() -> dict:
    path = Path(__file__).parent / "brand_config.yml"
    with open(path) as f:
        return yaml.safe_load(f)


def _build_research_block(research: dict, max_signals: int = 45) -> str:
    lines = []
    for s in research["signals"][:max_signals]:
        snippet = s["snippet"][:180].replace("\n", " ")
        lines.append(f"[{s['source']}] {s['title']} — {snippet}")
    return "\n".join(f"• {l}" for l in lines)


def select_topic(research: dict) -> dict:
    brand = _load_brand()
    b = brand["brand"]
    ig = brand["instagram"]
    canva_fields = list(brand["canva"]["autofill_fields"].keys())

    research_block = _build_research_block(research)

    system_prompt = (
        "You are an expert ESL social media content strategist. "
        "You always respond with a single valid JSON object and nothing else."
    )

    user_prompt = f"""## Brand Profile
Name: {b['name']}
Tagline: {b['tagline']}
Tone: {', '.join(b['tone'])}
Audience: {b['target_audience']['description']}
Levels: {', '.join(b['target_audience']['language_levels'])}
Audience goals: {', '.join(b['target_audience']['goals'])}
Pain points: {', '.join(b['target_audience']['pain_points'])}
Content pillars: {', '.join(b['content_pillars'])}
Avoid: {', '.join(b['avoid'])}

## Research Signals (collected today)
{research_block}

## Task
Choose ONE topic for an Instagram carousel that:
1. Is currently trending or highly relevant based on the signals above
2. Belongs to at least one content pillar
3. Directly addresses a real audience pain point
4. Works as a 6-slide carousel (hook + 4 teaching slides + CTA)
5. Gives practical, immediately usable value

Return ONLY a JSON object matching this schema exactly:

{{
  "topic": "<short topic name, e.g. 'make vs do'>",
  "pillar": "<which content pillar>",
  "audience_pain_point": "<which pain point this addresses>",
  "rationale": "<2-3 sentences: why this topic now, based on the signals>",
  "carousel": {{
    "hook_title": "<attention-grabbing headline, max 8 words>",
    "hook_subtitle": "<makes audience want to swipe, max 15 words>",
    "tip_1_heading": "<heading for slide 2, max 6 words>",
    "tip_1_body": "<clear teaching point, max 25 words>",
    "tip_2_heading": "<heading for slide 3, max 6 words>",
    "tip_2_body": "<clear teaching point, max 25 words>",
    "tip_3_heading": "<heading for slide 4, max 6 words>",
    "tip_3_body": "<clear teaching point, max 25 words>",
    "tip_4_heading": "<heading for slide 5, max 6 words>",
    "tip_4_body": "<clear teaching point, max 25 words>",
    "cta_heading": "<call-to-action heading, max 6 words>",
    "cta_body": "<CTA body + follow prompt, max 20 words>"
  }},
  "caption": "<full Instagram caption, max 2000 chars. Engaging opener, expand on the topic, end with: {ig['caption_cta']} then a blank line then the hashtags>",
  "hashtags": ["<tag without #>", "..."]
}}"""

    client = anthropic.Anthropic()
    logger.info("Calling Claude to select topic and generate carousel content…")

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt,
                        # Cache the large brand + research block — it won't change
                        # between retries or future calls with the same research.
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if the model wraps its output
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) >= 2 else raw

    result = json.loads(raw)

    # Truncate caption to Instagram's hard limit
    if len(result.get("caption", "")) > 2200:
        result["caption"] = result["caption"][:2197] + "…"

    logger.info(f"Selected topic: '{result['topic']}' (pillar: {result['pillar']})")
    logger.info(f"Rationale: {result['rationale']}")
    return result
