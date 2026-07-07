"""Any RSS/Atom feed — the wide-net catch-all.

Add feed URLs in Settings (one per line): tender boards, procurement portals,
NGO career pages, Google Alerts feeds, dgMarket categories, etc. Each new item
whose title/summary matches your keywords becomes a lead.

Tip: Google Alerts (google.com/alerts) can emit an RSS feed for queries like
  "request for proposals" "monitoring and evaluation" Zambia
which effectively turns Google's whole index into a lead source, legally.
"""
import feedparser

from services_catalog import combined_keywords

NAME = "RSS / Atom feeds"
DESCRIPTION = ("Pulls from any feed URLs you add in Settings — tender boards, "
               "procurement portals, Google Alerts. The widest legal net, filtered "
               "to NCE's 12 service lines plus generic procurement-demand terms.")
NEEDS = ["rss_urls"]

DEFAULT_KEYWORDS = combined_keywords() + [
    "rfp", "request for proposal", "request for quotation", "invitation to bid",
    "expression of interest", "tender",
]


def pull(settings: dict) -> list[dict]:
    urls = [u.strip() for u in (settings.get("rss_urls") or "").splitlines() if u.strip()]
    keywords = [k.strip().lower() for k in
                (settings.get("rss_keywords") or ",".join(DEFAULT_KEYWORDS)).split(",")
                if k.strip()]
    leads = []
    for url in urls[:15]:
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        feed_title = getattr(feed.feed, "title", url)[:80]
        for entry in feed.entries[:25]:
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")[:300]
            blob = (title + " " + summary).lower()
            if keywords and not any(k in blob for k in keywords):
                continue
            posted = ""
            if getattr(entry, "published_parsed", None):
                t = entry.published_parsed
                posted = f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}"
            leads.append({
                "org": feed_title if len(title) > 90 else title[:120] or feed_title,
                "trigger": f"the posting \"{title[:120]}\"",
                "notes": f"Via feed: {feed_title}. {summary}",
                "url": getattr(entry, "link", ""),
                "source": "RSS feed",
                "posted_date": posted,
                "dedupe_key": f"rss|{getattr(entry, 'link', title)[:180]}",
            })
    return leads
