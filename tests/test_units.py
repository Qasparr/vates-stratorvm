# ============================================================================
# 93
# VATES STRATORVM · tests — the law proven without a network.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
#
# MECHANISM: unittest, stdlib only. Four proving grounds: the SOCKS5
# reply parser, the dork composer, the HTML extractor, and the FTS
# index round-trip (add fixture pages, search, find). No test touches
# Tor, Google, or any live service.
# ============================================================================

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vates_stratorvm import google
from vates_stratorvm.fetch import extract_page
from vates_stratorvm.index import Index, host_hash, is_denied, load_denylist
from vates_stratorvm.socks5 import (Socks5Error, bound_address_length,
                                    parse_reply_header)

FIXTURE_A = """<html><head><title>Layer One — Surface</title>
<style>body { color: red; }</style></head>
<body><h1>The surface layer</h1>
<p>Strata and layers, the visible web.</p>
<script>var hidden = "scripttext";</script>
<a href="/b.html">deeper</a> <a href="http://other.onion/x">onion</a>
</body></html>"""

FIXTURE_B = """<html><head><title>Layer Two — Beneath</title></head>
<body><p>The onion layer beneath the surface, searchable strata.</p>
<a href="/a.html">back up</a></body></html>"""


class Socks5Parsing(unittest.TestCase):
    def test_reply_header_ok(self):
        rep, atyp = parse_reply_header(bytes([5, 0, 0, 1]))
        self.assertEqual((rep, atyp), (0, 1))

    def test_reply_header_bad_version(self):
        with self.assertRaises(Socks5Error):
            parse_reply_header(bytes([4, 0, 0, 1]))

    def test_reply_header_too_short(self):
        with self.assertRaises(Socks5Error):
            parse_reply_header(bytes([5, 0]))

    def test_bound_lengths(self):
        self.assertEqual(bound_address_length(1), 6)          # IPv4 + port
        self.assertEqual(bound_address_length(4), 18)         # IPv6 + port
        self.assertEqual(bound_address_length(3, 10), 13)     # len+host+port
        with self.assertRaises(Socks5Error):
            bound_address_length(3)                           # needs length
        with self.assertRaises(Socks5Error):
            bound_address_length(9)


class DorkComposition(unittest.TestCase):
    def test_plain_terms(self):
        self.assertEqual(google.build_query("open data"), "open data")

    def test_full_composition(self):
        q = google.build_query(
            "annual report", site="example.edu", filetype="pdf",
            intitle="annual report", inurl="reports", intext="budget",
            before="2026-01-01", after="2024-01-01",
            exclude=["draft"], or_terms=["audit", "review"])
        self.assertEqual(
            q,
            'annual report site:example.edu filetype:pdf '
            'intitle:"annual report" inurl:reports intext:budget '
            'before:2026-01-01 after:2024-01-01 -draft (audit OR review)')

    def test_phrase(self):
        self.assertEqual(google.build_query("", phrase="exact words"),
                         '"exact words"')

    def test_search_url_encodes(self):
        url = google.search_url("a b site:x.org")
        self.assertTrue(url.startswith("https://www.google.com/search?q="))
        self.assertIn("a+b", url)


class Extraction(unittest.TestCase):
    def test_title_text_links(self):
        title, text, links = extract_page(FIXTURE_A,
                                          "http://fixture.local/a.html")
        self.assertEqual(title, "Layer One — Surface")
        self.assertIn("surface layer", text)
        self.assertNotIn("scripttext", text)      # script bodies excluded
        self.assertNotIn("color: red", text)      # style bodies excluded
        self.assertIn("http://fixture.local/b.html", links)
        self.assertIn("http://other.onion/x", links)


class IndexRoundTrip(unittest.TestCase):
    def test_add_and_search(self):
        with tempfile.TemporaryDirectory() as td:
            idx = Index(os.path.join(td, "t.db"))
            try:
                idx.upsert_page("http://fixture.local/a.html",
                                *extract_page(FIXTURE_A,
                                              "http://fixture.local/"
                                              "a.html")[:2])
                idx.upsert_page("http://fixture.local/b.html",
                                *extract_page(FIXTURE_B,
                                              "http://fixture.local/"
                                              "b.html")[:2])
                self.assertEqual(idx.page_count(), 2)
                hits = idx.search("onion layer")
                self.assertTrue(hits)
                self.assertEqual(hits[0]["url"],
                                 "http://fixture.local/b.html")
                self.assertIn("[", hits[0]["snippet"])
                self.assertEqual(idx.search("nonexistentterm"), [])
            finally:
                idx.close()

    def test_denylist_hash_law(self):
        host = "u55adh3il2rs2y3amgiopirckqq5g2uo64g5zaxvtmbakqvtyy4c3lad" \
               ".onion"
        hashes = {host_hash(host)}
        self.assertTrue(is_denied(f"http://{host}/page", hashes))
        self.assertFalse(is_denied("http://other.onion/", hashes))

    def test_load_denylist_skips_comments(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as fh:
            fh.write("# comment\n\n  ABCDEF0123456789abcdef0123456789"
                     "  \n")
            path = fh.name
        try:
            self.assertEqual(load_denylist(path),
                             {"abcdef0123456789abcdef0123456789"})
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
