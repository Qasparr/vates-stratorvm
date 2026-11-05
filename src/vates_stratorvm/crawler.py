# ============================================================================
# 93
#
# VATES STRATORVM · crawler.py — the polite, capped, GET-only crawler.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Scientific Illuminism — Method of Science, Aim of Religion.
#
# Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All
# Rights Reserved, Without Prejudice.
#
# MECHANISM: breadth-first from the seed table. A page's outgoing links
# are sorted into three fates: same-service links are followed while
# depth remains; links to OTHER .onion services are registered as new
# seeds (discovery) and followed while depth remains; everything else
# (clear-web, non-HTTP, malformed) is ignored by the onion engine.
#
# DOCTRINE — the politeness law, built in rather than promised:
#   * GET only; no forms, no logins, no cookies, no bodies sent.
#   * A delay between fetches (default 1.0 s) — the crawler waits its
#     turn like a reader in a library, not a flood.
#   * A global page cap AND a per-service page cap; when either trips,
#     the crawl stops cleanly and says so.
#   * Denylisted address hashes are refused at every door: seed, queue,
#     and fetch.
#   * In proxy (Tor) mode only .onion hosts are fetched. Direct mode
#     (proxy=None) exists for local fixtures and tests, and only there
#     may a non-onion host be fetched.
# ============================================================================

import time
from collections import deque
from urllib.parse import urlsplit

from .fetch import FetchError, extract_page, fetch_http
from .index import host_of, is_denied

DEFAULT_PROXY = ("127.0.0.1", 9050)


def _is_onion(url):
    return host_of(url).endswith(".onion")


def crawl(index, max_depth=2, max_pages=50, per_host_cap=25, delay=1.0,
          proxy=DEFAULT_PROXY, denylist_hashes=frozenset(),
          timeout=30.0):
    """Run one crawl over the index's seed table. Returns a stats dict:
    fetched, skipped (with reasons counted), seeds discovered."""
    stats = {"fetched": 0, "denied": 0, "off_scope": 0, "errors": 0,
             "seeds_discovered": 0, "capped": False}
    queue = deque()
    queued = set()
    for seed in index.seeds():
        if is_denied(seed, denylist_hashes):
            stats["denied"] += 1
            continue
        queue.append((seed, 0))
        queued.add(seed)

    per_host = {}
    while queue:
        if stats["fetched"] >= max_pages:
            stats["capped"] = True
            break
        url, depth = queue.popleft()
        host = host_of(url)

        # Scope law: Tor mode is onion-only; direct mode is test-only.
        if proxy is not None and not _is_onion(url):
            stats["off_scope"] += 1
            continue
        if is_denied(url, denylist_hashes):
            stats["denied"] += 1
            continue
        if per_host.get(host, 0) >= per_host_cap:
            continue
        if index.has_page(url):
            continue

        if delay:
            time.sleep(delay)
        try:
            status, headers, body = fetch_http(url, proxy=proxy,
                                               timeout=timeout)
        except Exception:
            stats["errors"] += 1
            continue
        if status != 200:
            stats["errors"] += 1
            continue
        content_type = headers.get("content-type", "text/html")
        if "text/html" not in content_type and "text/plain" not in \
                content_type:
            stats["off_scope"] += 1
            continue

        html_text = body.decode("utf-8", errors="replace")
        title, text, links = extract_page(html_text, url)
        index.upsert_page(url, title, text)
        stats["fetched"] += 1
        per_host[host] = per_host.get(host, 0) + 1

        if depth >= max_depth:
            continue
        for link in links:
            link_host = host_of(link)
            if not link.startswith("http://"):
                continue
            if is_denied(link, denylist_hashes):
                stats["denied"] += 1
                continue
            if proxy is not None and not _is_onion(link):
                continue  # the onion engine does not chase the clear web
            if link_host != host and _is_onion(link):
                # Discovery: a new service is a new seed, on the record.
                before = len(index.seeds())
                index.add_seed(link)
                if len(index.seeds()) > before:
                    stats["seeds_discovered"] += 1
            if link not in queued and not index.has_page(link):
                queue.append((link, depth + 1))
                queued.add(link)
    return stats
