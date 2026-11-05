# ============================================================================
# 93
#
# VATES STRATORVM · index.py — the local index: SQLite + FTS5.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Scientific Illuminism — Method of Science, Aim of Religion.
#
# Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All
# Rights Reserved, Without Prejudice.
#
# MECHANISM: three tables. `seeds` — the registered starting addresses.
# `pages` — one row per fetched page (url, host, title, text). `pages_fts`
# — an FTS5 virtual table mirroring url/title/text, searched with BM25
# ranking and snippet() highlighting. The index is a local file under the
# operator's control; nothing leaves the machine.
#
# DOCTRINE: the denylist is enforced by ADDRESS HASH. Ahmia publishes its
# blacklist as MD5 sums of onion domains; this index speaks the same
# language — host_hash() is the MD5 of the full host (e.g.
# "example....onion"), and any host whose hash is listed is refused at
# the door: never seeded, never fetched, never stored.
# ============================================================================

import hashlib
import os
import sqlite3
import time


def host_of(url):
    """The bare host of a URL, lower-cased, without port."""
    host = url.split("://", 1)[-1].split("/")[0].split("@")[-1]
    return host.split(":")[0].lower()


def host_hash(host):
    """MECHANISM: MD5 of the host string — the Ahmia blacklist format."""
    return hashlib.md5(host.encode("utf-8")).hexdigest()


def load_denylist(path):
    """MECHANISM: a denylist file is one MD5 host hash per line; blank
    lines and #-comments are documentation, not data. Missing file ==
    empty list (the shipped default), never an error."""
    hashes = set()
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip().lower()
                if line and not line.startswith("#"):
                    hashes.add(line.split()[0])
    return hashes


def is_denied(url, denylist_hashes):
    return host_hash(host_of(url)) in denylist_hashes


class Index:
    """The index itself: open (or create) the database file and work."""

    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)),
                    exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS seeds (
                url TEXT PRIMARY KEY,
                added_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                host TEXT NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                url, title, text
            );
            """)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # -- seeds ---------------------------------------------------------
    def add_seed(self, url):
        self.conn.execute(
            "INSERT OR IGNORE INTO seeds (url, added_at) VALUES (?, ?)",
            (url, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        self.conn.commit()

    def seeds(self):
        return [r[0] for r in
                self.conn.execute("SELECT url FROM seeds ORDER BY url")]

    # -- pages ---------------------------------------------------------
    def has_page(self, url):
        return self.conn.execute(
            "SELECT 1 FROM pages WHERE url = ?", (url,)).fetchone() \
            is not None

    def upsert_page(self, url, title, text):
        """MECHANISM: one row per URL in `pages`, one row per URL in the
        FTS mirror; re-fetching a page replaces, never duplicates."""
        host = host_of(url)
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.conn.execute(
            "INSERT INTO pages (url, host, title, text, fetched_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(url) DO UPDATE SET "
            "host=excluded.host, title=excluded.title, "
            "text=excluded.text, fetched_at=excluded.fetched_at",
            (url, host, title, text, now))
        self.conn.execute("DELETE FROM pages_fts WHERE url = ?", (url,))
        self.conn.execute(
            "INSERT INTO pages_fts (url, title, text) VALUES (?, ?, ?)",
            (url, title, text))
        self.conn.commit()

    def page_count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM pages").fetchone()[0]

    # -- search --------------------------------------------------------
    def search(self, query, limit=10):
        """MECHANISM: FTS5 MATCH over title+text, BM25 for rank (lower
        is better in FTS5, so it is negated for display), snippet() for
        the excerpt around the hit. The query is quoted term-by-term so
        user input is data for the matcher, never FTS syntax."""
        terms = [t.replace('"', " ") for t in query.split() if t.strip()]
        if not terms:
            return []
        match = " ".join(f'"{t}"' for t in terms)
        rows = self.conn.execute(
            "SELECT url, title, "
            "snippet(pages_fts, 2, '[', ']', ' … ', 14), "
            "-bm25(pages_fts) AS score "
            "FROM pages_fts WHERE pages_fts MATCH ? "
            "ORDER BY score DESC LIMIT ?",
            (match, limit)).fetchall()
        return [{"url": r[0], "title": r[1], "snippet": r[2],
                 "score": r[3]} for r in rows]
