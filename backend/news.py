"""
Market news for the home page: real headlines about online retail, the Nigerian
stock market and digital marketing, pulled from Bing News RSS. Only the headline,
source, image and a link to the original article are shown. Results are cached
so the home page never waits on the network.
"""
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

TOPICS = [
    ("ecommerce", "E-commerce", "fa-cart-shopping", "Nigeria e-commerce online shopping"),
    ("stocks", "Stock market", "fa-chart-line", "Nigerian Exchange NGX stock market"),
    ("marketing", "Digital marketing", "fa-bullhorn", "digital marketing Nigeria social media advertising"),
    ("fintech", "Fintech & payments", "fa-credit-card", "Nigeria fintech payments online retail"),
]
PER_TOPIC = 6
CACHE_SECONDS = 30 * 60
RSS_URL = "https://www.bing.com/news/search?q={q}&format=rss"

_cache = {"at": 0, "data": None}
_lock = threading.Lock()


def _local_tag(tag):
    return tag.rsplit("}", 1)[-1]


def _original_link(link):
    """Bing wraps the publisher URL in a redirect; pull the real URL back out."""
    query = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
    target = (query.get("url") or [link])[0]
    return target if target.startswith(("http://", "https://")) else None


def _fetch_topic(topic):
    key, title, icon, query = topic
    items = []
    try:
        req = urllib.request.Request(
            RSS_URL.format(q=urllib.parse.quote_plus(query)), headers={"User-Agent": "Mozilla/5.0"}
        )
        root = ET.fromstring(urllib.request.urlopen(req, timeout=8).read())
        for item in root.iter("item"):
            fields = {_local_tag(c.tag): (c.text or "").strip() for c in item}
            link = _original_link(fields.get("link", ""))
            if not link or not fields.get("title"):
                continue
            image = fields.get("Image", "")
            if image:
                image = image.replace("http://", "https://", 1) + "&w=480&h=270&c=14"
            try:
                published = parsedate_to_datetime(fields.get("pubDate", "")).timestamp()
            except (TypeError, ValueError):
                published = 0
            items.append({
                "title": fields["title"], "url": link, "source": fields.get("Source", ""),
                "image": image, "published": published,
            })
            if len(items) == PER_TOPIC:
                break
    except Exception:
        pass
    return {"key": key, "title": title, "icon": icon, "items": items}


def get_news():
    with _lock:
        fresh = _cache["data"] and time.time() - _cache["at"] < CACHE_SECONDS
        if fresh:
            return _cache["data"]
        with ThreadPoolExecutor(max_workers=len(TOPICS)) as pool:
            topics = list(pool.map(_fetch_topic, TOPICS))
        if any(t["items"] for t in topics):
            _cache["data"], _cache["at"] = {"topics": topics, "updated": time.time()}, time.time()
            return _cache["data"]
        # Network trouble: keep serving the last good copy if there is one
        return _cache["data"] or {"topics": topics, "updated": None}
