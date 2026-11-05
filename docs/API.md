# VATES STRATORVM — API & Command Reference

**VATES STRATORVM — SOL, the Seer of Layers.**

*Authorship attributed exclusively to Johnathan 'Qasparr' Monroe (Greek, -ARR, All Rights Reserved, Without Prejudice). Method of Science, Aim of Religion.*

This document is the full surface: every command, every flag, the dork-operator table, the index schema, the environment variables, and the Python module API. The [README](../README.md) is the front door; this is the engine room.

---

## 1. Global flags

Both console scripts are the same instrument: `vates-stratorvm` and its short alias `vates`. (`python3 -m vates_stratorvm` is equivalent.)

| Flag | Default | Meaning |
|---|---|---|
| `--db PATH` | `~/.vates-stratorvm/index.db` (or `$VATES_DB`) | SQLite index file. Created on first use. |
| `--denylist PATH` | the repo's `denylist.txt` | File of MD5 host hashes to refuse (see §6). |
| `--help` | — | Usage for the CLI or any subcommand. |

Global flags come **before** the subcommand: `vates --db /tmp/x.db search "term"`.

## 2. Commands

### `index add <url>`

Register one seed address in the index's seed table.

- Refused (exit 1) if the URL's host hash is on the denylist.
- Idempotent: re-adding an existing seed changes nothing.

### `index crawl`

Crawl from every registered seed. If the seed table is empty, the founding seeds load automatically (the Bleats onion and Ahmia's onion — see `seeds.txt`).

| Flag | Default | Meaning |
|---|---|---|
| `--depth N` | 2 | Maximum link depth from a seed. |
| `--max-pages M` | 50 | Global page cap. Hard stop. |
| `--per-host N` | 25 | Per-service page cap. Hard stop. |
| `--delay S` | 1.0 | Seconds between fetches (politeness law). |
| `--seeds-file PATH` | — | Load additional seeds from a file (one URL per line, `#` comments) before crawling. |
| `--direct` | off | **Test mode only:** fetch directly with no Tor proxy, allowing non-onion hosts (local fixtures). |

Behaviour, in law: GET only; Tor mode fetches `.onion` hosts only; same-service links are followed while depth remains; links to other `.onion` services are registered as new seeds (discovery) and followed while depth remains; denylisted hosts are refused at seed, queue, and fetch; only `text/html` / `text/plain` 200 responses are indexed. Prints a completion line: pages indexed, seeds discovered, denylisted refused, fetch errors, cap notice.

### `search <query> [--limit N]`

Search the local onion index. Default limit 10.

- The query is split into terms; each term is matched as a quoted FTS5 phrase, so user input is matcher data, never FTS syntax.
- Ranking is BM25 over title + text; output per hit: title, URL, and a `snippet()` excerpt with the matched terms bracketed (`[term]`).
- No hits prints `(no hits in the local onion index)` — which means *not yet indexed*, never *does not exist*.

### `web <terms> [dork flags]`

Compose a Google query from structured flags (see §3), then:

1. Print the composed query.
2. Print its `https://www.google.com/search?q=…` URL.
3. **If** `GOOGLE_API_KEY` and `GOOGLE_CX` are both set, run it through the Google Custom Search JSON API and print results (title, link, snippet). API errors are reported as errors, never disguised as empty results.

Google result pages are never scraped, in any mode.

### `search-all <terms> [dork flags] [--limit N]`

One output, both layers: the onion-index search for the terms, then the clear-engine output exactly as `web` produces it.

## 3. Dork operator table

Shared verbatim by `web` and `search-all`.

| Flag | Operator composed | Example |
|---|---|---|
| *(positional terms)* | free terms | `annual report` |
| `--phrase "…"` | `"exact phrase"` | `"open data"` |
| `--site X` | `site:X` | `site:example.edu` |
| `--filetype X` | `filetype:X` | `filetype:pdf` |
| `--intitle X` | `intitle:X` (quoted if spaced) | `intitle:"data portal"` |
| `--inurl X` | `inurl:X` | `inurl:reports` |
| `--intext X` | `intext:X` | `intext:budget` |
| `--before YYYY-MM-DD` | `before:…` | `before:2026-01-01` |
| `--after YYYY-MM-DD` | `after:…` | `after:2024-01-01` |
| `--exclude X` *(repeatable)* | `-X` | `-draft` |
| `--or X` *(repeatable)* | `(A OR B)` group | `(audit OR review)` |

Composition order is fixed: phrase, terms, `site:`, `filetype:`, `intitle:`, `inurl:`, `intext:`, `before:`, `after:`, exclusions, OR group. The composer is neutral — it assembles what it is given and invents nothing; the package ships no preset dorks.

## 4. Environment variables

| Variable | Used by | Meaning |
|---|---|---|
| `VATES_DB` | CLI | Default index DB path (overridden by `--db`). |
| `GOOGLE_API_KEY` | `web`, `search-all` | The operator's own Google API key for the Custom Search JSON API. Never stored by the tool. |
| `GOOGLE_CX` | `web`, `search-all` | The operator's own Programmable Search engine ID. |

## 5. Index database schema (SQLite)

```sql
CREATE TABLE seeds (
    url      TEXT PRIMARY KEY,
    added_at TEXT NOT NULL          -- ISO-8601 UTC
);
CREATE TABLE pages (
    url        TEXT PRIMARY KEY,
    host       TEXT NOT NULL,
    title      TEXT NOT NULL,
    text       TEXT NOT NULL,       -- visible text, whitespace-collapsed
    fetched_at TEXT NOT NULL        -- ISO-8601 UTC
);
CREATE VIRTUAL TABLE pages_fts USING fts5(url, title, text);
```

`pages_fts` mirrors `pages` one row per URL; re-fetching a page replaces both rows. Search is `pages_fts MATCH <terms>` ordered by `-bm25(pages_fts)`.

## 6. Denylist format

One entry per line: the **MD5 hash (32 lowercase hex) of a full onion host** — the Ahmia blacklist format. Blank lines and `#` lines are documentation. A listed host is refused at every door: `index add`, the crawl queue, and fetch. The shipped file is empty; operators should load Ahmia's published blacklist before crawling beyond their own seeds.

## 7. Python module API

For embedding, not just shelling out:

| Module | Surface |
|---|---|
| `vates_stratorvm.socks5` | `connect_via_socks5(proxy_host, proxy_port, dest_host, dest_port, timeout=30.0) -> socket`; helpers `parse_reply_header(bytes) -> (rep, atyp)`, `bound_address_length(atyp, first_byte=None)`; exception `Socks5Error`. |
| `vates_stratorvm.fetch` | `fetch_http(url, proxy=None, timeout=30.0) -> (status, headers, body)` — proxy `None` is direct/test mode, `(host, port)` is a SOCKS5 tunnel; `extract_page(html_text, base_url) -> (title, text, links)`; exception `FetchError`. Plain HTTP only in v0.1. |
| `vates_stratorvm.index` | `Index(db_path)` with `.add_seed(url)`, `.seeds()`, `.has_page(url)`, `.upsert_page(url, title, text)`, `.page_count()`, `.search(query, limit=10) -> [{url, title, snippet, score}]`, `.close()`; helpers `host_of(url)`, `host_hash(host)`, `load_denylist(path) -> set`, `is_denied(url, hashes)`. |
| `vates_stratorvm.crawler` | `crawl(index, max_depth=2, max_pages=50, per_host_cap=25, delay=1.0, proxy=("127.0.0.1", 9050), denylist_hashes=frozenset(), timeout=30.0) -> stats` where stats = `{fetched, denied, off_scope, errors, seeds_discovered, capped}`. |
| `vates_stratorvm.google` | `build_query(terms, site=None, filetype=None, intitle=None, inurl=None, intext=None, before=None, after=None, exclude=(), or_terms=(), phrase=None) -> str`; `search_url(query) -> str`; `run_custom_search(query, api_key, cx, num=10) -> [{title, link, snippet}]`. |
| `vates_stratorvm.cli` | `main(argv=None) -> int` — the console entry point for both script names. |

## 8. Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (including a search with no hits). |
| 1 | A denylisted seed was refused at `index add`. |
| 2 | Command-line usage error (argparse). |

---

*Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All Rights Reserved, Without Prejudice.*

**93 — Live, Love, and let Love, Live.**
