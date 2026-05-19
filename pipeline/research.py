"""
Step 1 — Market Research
Collects trending ESL/language-learning signals from Reddit, DuckDuckGo,
and Google Trends.  All three sources are free; Reddit requires a free
API app (see README for setup).
"""
import os
import logging
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    source: str
    title: str
    snippet: str
    url: str = ""
    score: float = 0.0


# ── Reddit ────────────────────────────────────────────────────────────────────

def _reddit_signals(limit: int = 20) -> list[Signal]:
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.warning("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set — skipping Reddit")
        return []

    import praw

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="ESLContentPipeline/1.0 (by u/yourRedditUsername)",
    )

    subreddits = ["TEFL", "languagelearning", "EnglishLearning", "esl"]
    signals: list[Signal] = []

    for sub in subreddits:
        try:
            for post in reddit.subreddit(sub).hot(limit=limit):
                if post.score < 15:
                    continue
                signals.append(Signal(
                    source=f"Reddit r/{sub}",
                    title=post.title,
                    snippet=(post.selftext[:300] if post.selftext else "(link post)"),
                    url=f"https://reddit.com{post.permalink}",
                    score=float(post.score),
                ))
            logger.info(f"  Reddit r/{sub}: {len(signals)} signals so far")
        except Exception as exc:
            logger.warning(f"  Reddit r/{sub} failed: {exc}")

    return signals


# ── DuckDuckGo web search ─────────────────────────────────────────────────────

def _web_signals() -> list[Signal]:
    from duckduckgo_search import DDGS

    queries = [
        "trending ESL grammar topics Instagram 2025",
        "most shared English learning tips social media",
        "common English mistakes adults make at work",
        "ESL content ideas viral posts language learning",
        "English vocabulary tips professionals 2025",
    ]
    signals: list[Signal] = []

    with DDGS() as ddgs:
        for query in queries:
            try:
                for r in ddgs.text(query, max_results=8):
                    signals.append(Signal(
                        source="Web search",
                        title=r.get("title", ""),
                        snippet=r.get("body", "")[:300],
                        url=r.get("href", ""),
                    ))
            except Exception as exc:
                logger.warning(f"  DDG query '{query}' failed: {exc}")

    logger.info(f"  Web search: {len(signals)} signals")
    return signals


# ── Google Trends ─────────────────────────────────────────────────────────────

def _trends_signals() -> list[Signal]:
    from pytrends.request import TrendReq

    keywords = ["ESL", "learn English", "English grammar", "English tips", "IELTS"]
    signals: list[Signal] = []

    try:
        pt = TrendReq(hl="en-US", tz=0)
        pt.build_payload(keywords, timeframe="now 7-d")
        related = pt.related_queries()

        for kw, data in related.items():
            rising = data.get("rising")
            if rising is not None and not rising.empty:
                for _, row in rising.head(5).iterrows():
                    signals.append(Signal(
                        source="Google Trends",
                        title=f"Rising query: {row['query']}",
                        snippet=f"Related to '{kw}' — relative value {row['value']}",
                    ))
    except Exception as exc:
        logger.warning(f"  Google Trends failed: {exc}")

    logger.info(f"  Google Trends: {len(signals)} signals")
    return signals


# ── Public entry point ────────────────────────────────────────────────────────

def run_research() -> dict:
    logger.info("Starting market research…")

    reddit = _reddit_signals()
    web = _web_signals()
    trends = _trends_signals()
    all_signals = reddit + web + trends

    logger.info(
        f"Research done — {len(all_signals)} total signals "
        f"(Reddit: {len(reddit)}, Web: {len(web)}, Trends: {len(trends)})"
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "counts": {"reddit": len(reddit), "web": len(web), "trends": len(trends)},
        "signals": [asdict(s) for s in all_signals],
    }
