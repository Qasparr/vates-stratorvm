# ============================================================================
# 93
#
# "Do what thou wilt shall be the whole of the Law."
#
# VATES STRATORVM — SOL, the Seer of Layers: one search instrument for
# the layered web. (Callsign SOL — Seer Of Layers; sol, the sun, the
# light that sees through the layers.) The onion engine below (crawl +
# local index, built ground up over
# a hand-written SOCKS5 client); the clear engine beside it (a Google-
# dork composer that uses Google where Google is needed, through its own
# API or a composed URL). Everything else is this house's own work.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# V day of November, Dies Iovis, Sol in Scorpio, Anno V:xii e.n. (2026 e.v.)
#
# Classification: Enterprise • Educational • Research & Development
# Method of Science, Aim of Religion.
#
# Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All
# Rights Reserved, Without Prejudice. Right of claim hereby reserved and
# coined under the authority of the Living Man.
#
# ----------------------------------------------------------------------------
# CONTENT TEST (the four-element engineering spec)
#   Inputs:    seed .onion addresses; pages fetched over Tor (SOCKS5 at
#              127.0.0.1:9050); search terms; dork flags; optionally the
#              operator's GOOGLE_API_KEY / GOOGLE_CX.
#   Processes: polite GET-only crawl -> title/text/link extraction ->
#              SQLite FTS5 index -> BM25 search; and operator-composed
#              Google queries -> Custom Search API or a printed URL.
#   Outputs:   a local index file; ranked search results with snippets;
#              composed dork queries and their URLs / API results.
#   Tolerances: page caps and per-service caps are hard stops; denylist
#              hashes are refused at every door; no form is ever
#              submitted; no Google result page is ever scraped.
# ----------------------------------------------------------------------------
# ============================================================================

import argparse
import os
import sys

from . import google
from .crawler import DEFAULT_PROXY, crawl
from .index import Index, is_denied, load_denylist

DEFAULT_DB = os.environ.get(
    "VATES_DB",
    os.path.join(os.path.expanduser("~"), ".vates-stratorvm", "index.db"))
DEFAULT_DENYLIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "denylist.txt")

# The founding seeds: the house's own onion, and Ahmia's — the index
# this instrument aligns itself with (legal services indexed, abuse
# material blacklisted).
DEFAULT_SEEDS = [
    "http://u55adh3il2rs2y3amgiopirckqq5g2uo64g5zaxvtmbakqvtyy4c3lad"
    ".onion/",
    "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd"
    ".onion/",
]


def _add_dork_flags(parser):
    """The dork composer's structured flags, shared by `web` and
    `search-all` so the two doors can never drift apart."""
    parser.add_argument("--site")
    parser.add_argument("--filetype")
    parser.add_argument("--intitle")
    parser.add_argument("--inurl")
    parser.add_argument("--intext")
    parser.add_argument("--before", help="YYYY-MM-DD")
    parser.add_argument("--after", help="YYYY-MM-DD")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--or", dest="or_terms", action="append",
                        default=[])
    parser.add_argument("--phrase", help="exact-phrase terms")


def _compose(args):
    return google.build_query(
        args.terms, site=args.site, filetype=args.filetype,
        intitle=args.intitle, inurl=args.inurl, intext=args.intext,
        before=args.before, after=args.after, exclude=args.exclude,
        or_terms=args.or_terms, phrase=args.phrase)


def _print_web(args):
    """The clear engine's output: the composed query always; the URL
    always; API results when the operator's own key + CX are present."""
    query = _compose(args)
    print(f"Query: {query}")
    print(f"URL:   {google.search_url(query)}")
    api_key, cx = os.environ.get("GOOGLE_API_KEY"), \
        os.environ.get("GOOGLE_CX")
    if api_key and cx:
        try:
            results = google.run_custom_search(query, api_key, cx)
        except Exception as e:
            print(f"Custom Search API error: {e}")
            return
        print("\nResults (Google Custom Search API):")
        if not results:
            print("  (no results returned)")
        for r in results:
            print(f"  {r['title']}\n    {r['link']}\n    {r['snippet']}")
    else:
        print("(GOOGLE_API_KEY / GOOGLE_CX not set — composed URL only; "
              "no Google call was made.)")


def _print_onion_results(index, query, limit):
    results = index.search(query, limit=limit)
    if not results:
        print("  (no hits in the local onion index)")
    for r in results:
        print(f"  {r['title'] or '(untitled)'}")
        print(f"    {r['url']}")
        print(f"    {r['snippet']}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="vates-stratorvm",
        description="VATES STRATORVM — seer of layers: onion index "
                    "search + Google-dork composer in one instrument.")
    parser.add_argument("--db", default=DEFAULT_DB,
                        help=f"index database (default: {DEFAULT_DB})")
    parser.add_argument("--denylist", default=DEFAULT_DENYLIST,
                        help="file of MD5 host hashes to refuse")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="seed and crawl the onion "
                                           "index")
    index_sub = p_index.add_subparsers(dest="index_command",
                                       required=True)
    p_add = index_sub.add_parser("add", help="register a seed address")
    p_add.add_argument("url")
    p_crawl = index_sub.add_parser("crawl", help="crawl from the seeds")
    p_crawl.add_argument("--depth", type=int, default=2)
    p_crawl.add_argument("--max-pages", type=int, default=50)
    p_crawl.add_argument("--per-host", type=int, default=25)
    p_crawl.add_argument("--delay", type=float, default=1.0)
    p_crawl.add_argument("--seeds-file",
                         help="load additional seeds from a file first")
    p_crawl.add_argument("--direct", action="store_true",
                         help="TEST MODE: fetch directly, no Tor proxy "
                              "(local fixtures only)")

    p_search = sub.add_parser("search", help="search the onion index")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10)

    p_web = sub.add_parser("web", help="compose (and optionally run) a "
                                       "Google dork query")
    p_web.add_argument("terms")
    _add_dork_flags(p_web)

    p_all = sub.add_parser("search-all", help="onion index + Google "
                                              "query, one output")
    p_all.add_argument("terms")
    p_all.add_argument("--limit", type=int, default=10)
    _add_dork_flags(p_all)

    args = parser.parse_args(argv)
    denylist = load_denylist(args.denylist)

    if args.command == "web":
        _print_web(args)
        return 0

    index = Index(args.db)
    try:
        if args.command == "index" and args.index_command == "add":
            if is_denied(args.url, denylist):
                print("Refused: this address is on the denylist.")
                return 1
            index.add_seed(args.url)
            print(f"Seed registered: {args.url}")
            return 0

        if args.command == "index" and args.index_command == "crawl":
            if not index.seeds():
                for seed in DEFAULT_SEEDS:
                    index.add_seed(seed)
                print("Seed table was empty; founding seeds loaded "
                      "(Bleats + Ahmia).")
            if args.seeds_file:
                with open(args.seeds_file, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            index.add_seed(line)
            proxy = None if args.direct else DEFAULT_PROXY
            stats = crawl(index, max_depth=args.depth,
                          max_pages=args.max_pages,
                          per_host_cap=args.per_host, delay=args.delay,
                          proxy=proxy, denylist_hashes=denylist)
            print(f"Crawl complete: {stats['fetched']} pages indexed, "
                  f"{stats['seeds_discovered']} new seeds discovered, "
                  f"{stats['denied']} denylisted refused, "
                  f"{stats['errors']} fetch errors"
                  f"{' (page cap reached)' if stats['capped'] else ''}.")
            print(f"Index now holds {index.page_count()} pages, "
                  f"{len(index.seeds())} seeds.")
            return 0

        if args.command == "search":
            _print_onion_results(index, args.query, args.limit)
            return 0

        if args.command == "search-all":
            print("== Onion index (local) ==")
            _print_onion_results(index, args.terms, args.limit)
            print("\n== Clear web (Google) ==")
            _print_web(args)
            return 0
    finally:
        index.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# Colophon: generated under the Doctrine, exclusive authorship as above,
# ARR/WP. Method of Science. Aim of Religion.
#
# Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All
# Rights Reserved, Without Prejudice.
#
# 93 — Live, Love, and let Love, Live.
# ============================================================================
