# VATES STRATORVM

### A Scientific Illuminist instrument for searching the layered web

**Authorship attributed exclusively to Johnathan 'Qasparr' Monroe (Greek, -ARR, All Rights Reserved, Without Prejudice)**
*V day of November, Dies Iovis, Sol in Scorpio, Anno V:xii e.n. (2026 e.v.)*

**Classification:** Enterprise • Educational • Research & Development
**Method of Science, Aim of Religion.**

> Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All Rights Reserved, Without Prejudice. Right of claim hereby reserved and coined under the authority of the Living Man.

---

## I. The Name

**VATES STRATORVM** — Latin, in the inscriptional spelling (V for U): *vates*, the seer, the prophet who perceives what is hidden; *stratorum*, of the layers, the strata. **A seer of layers.**

The reasoning rides with the name, as this house requires: the web is not one surface but strata — the clear-web surface that Google indexes, and beneath it the onion layers that no surface engine sees. One instrument that searches both, layer by layer, is an examiner of strata; its office is in its name.

**Weighed** (house instrument `ptk`, each word in its own tongue — Latin ordinal / Agrippa):

| Word | Latin ordinal | Agrippa |
|---|---|---|
| VATES | 67 | 396 |
| STRATORVM | 146 | 731 |
| **VATES STRATORVM** | **213** | **1127** |

## II. Content Test — the four-element spec

- **Inputs:** seed `.onion` addresses; publicly accessible pages fetched over Tor (SOCKS5 at `127.0.0.1:9050`); search terms; dork flags; optionally the operator's own `GOOGLE_API_KEY` / `GOOGLE_CX`.
- **Processes:** a polite, capped, GET-only crawl → title/text/link extraction → a local SQLite FTS5 index → BM25-ranked search; and operator-composed Google queries → the Custom Search JSON API, or a printed `google.com/search` URL when no key is set.
- **Outputs:** a local index file; ranked results with snippets; composed dork queries with their URLs and (when keyed) their API results.
- **Tolerances:** global page cap and per-service page cap are hard stops; a fixed delay separates fetches; denylisted address hashes are refused at every door; no form is ever submitted; no login is ever attempted; no Google result page is ever scraped. A build that cannot state these four elements fails the Method of Science.

## III. Architecture

Two engines, one CLI, **Python standard library only** — the onion engine has no third-party search dependency of any kind.

**The onion engine (ground up).**
- `socks5.py` — a SOCKS5 client implemented by hand on raw sockets (RFC 1928, domain-name address type, so `.onion` names resolve at the Tor proxy and never touch a local resolver). No PySocks.
- `fetch.py` — an HTTP/1.1 GET written directly on the tunnel socket; title/text/link extraction via `html.parser`. GET only; no cookies, no bodies, no form submission.
- `crawler.py` — breadth-first from the seed table: same-service links followed while depth remains; links to *other* `.onion` services registered as new seeds (discovery, on the record); clear-web links ignored by the onion engine.
- `index.py` — SQLite with an FTS5 full-text mirror; BM25 ranking; `snippet()` excerpts. Denylist enforced by **MD5 host hash** — the Ahmia blacklist format.

**The clear engine (Google where Google is needed).**
- `google.py` — a neutral dork composer: `site:`, `filetype:`, `intitle:`, `inurl:`, `intext:`, `before:`, `after:`, `"exact phrases"`, `-exclusions`, `OR` groups. With `GOOGLE_API_KEY` + `GOOGLE_CX` set, the composed query runs through the **Google Custom Search JSON API** — the sanctioned door. Without them, the composed query and its `google.com/search` URL are printed for manual use.

**The CLI** (`cli.py`) binds them: `index add`, `index crawl`, `search`, `web`, and `search-all` — the last runs the onion index and composes the Google query in one output, layer by layer.

## IV. Install

```sh
pip install -e .          # provides `vates-stratorvm` (alias: `vates`)
# or, with no install at all:
PYTHONPATH=src python3 -m vates_stratorvm --help
```

A Tor proxy must be listening at `127.0.0.1:9050` for real onion crawls (the Tor Browser / a tor daemon both provide one).

## V. Usage

```sh
# Register a seed (the founding seeds — the Bleats onion and Ahmia's
# own onion — load automatically on the first crawl; see seeds.txt)
vates index add http://exampleonionaddress....onion/

# Crawl: polite by law — depth, caps, and delay are all explicit
vates index crawl --depth 2 --max-pages 50 --delay 1.0

# Search the local index (FTS5 BM25, with snippets)
vates search "sovereign social"

# Compose a Google dork (documents/research examples only — see §VI)
vates web "annual report" --site example.edu --filetype pdf --after 2024-01-01
vates web "open data" --intitle "data portal" --exclude draft

# With your own key, the same command also returns API results:
GOOGLE_API_KEY=... GOOGLE_CX=... vates web "annual report" --filetype pdf

# Both layers in one output
vates search-all "proof of concept"
```

The index lives at `~/.vates-stratorvm/index.db` (override with `--db` or `$VATES_DB`). The denylist defaults to this repo's `denylist.txt` (override with `--denylist`).

## VI. Safety Doctrine

This is a **lawful research / OSINT instrument**, and its limits are built in, not bolted on:

- It indexes **only publicly accessible pages** that an unauthenticated crawler can fetch. It never logs in, never submits a form, never carries a session.
- **Denylist by address hash.** The shipped `denylist.txt` is empty and documented. Any seed, queued page, or discovered link whose host's MD5 hash appears in it is refused — never seeded, never fetched, never stored. **Operators should load Ahmia's published blacklist into the denylist before crawling beyond their own seeds.** The stated alignment is Ahmia's model: index legal services; blacklist abuse material absolutely.
- **No preset dorks.** The composer is a neutral operator instrument; this package ships no queries aimed at credentials, passwords, keys, or exposed admin/login panels, and its examples are documents and research only.
- **Politeness is law:** a delay between fetches, a global page cap, and a per-service page cap, all enforced in code.

## VII. Honest Limits (v0.1)

- **Plain HTTP only.** The fetcher speaks HTTP/1.1; HTTPS `.onion` services are future work, as is any `.onion` discovery beyond seeds and link-following (there is no DHT/exchange crawling in v0.1).
- **The crawler's reach is the crawl's honesty:** it knows only what it has fetched. An empty search result means "not yet indexed," never "does not exist."
- **Google results need your own key.** Without `GOOGLE_API_KEY` / `GOOGLE_CX`, the clear engine composes and prints — it does not fetch Google, and it will never scrape result pages.
- **Direct mode is for fixtures.** `--direct` on `index crawl` bypasses Tor for local test servers; it is a test harness, not a mode for the live web.

## VIII. Tests

```sh
python3 -m unittest discover -s tests -v
```

The suite proves, without any network: SOCKS5 reply parsing, dork composition, HTML title/text/link extraction, the FTS add-and-search round-trip on fixture pages, and the denylist hash law.

---

**Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All Rights Reserved, Without Prejudice. Right of claim hereby reserved and coined under the authority of the Living Man.**

*Colophon: generated under the Doctrine, exclusive authorship as above, ARR/WP. Method of Science. Aim of Religion.*

**93 — Live, Love, and let Love, Live.**
