# ============================================================================
# 93
#
# VATES STRATORVM · fetch.py — plain-HTTP fetching and page extraction.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Scientific Illuminism — Method of Science, Aim of Religion.
#
# Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All
# Rights Reserved, Without Prejudice.
#
# MECHANISM: an HTTP/1.1 GET written directly on a socket — either a
# direct socket (test mode) or a SOCKS5 tunnel from socks5.py (onion
# mode). `Connection: close` is requested so the body is read to EOF;
# chunked transfer-encoding is decoded when a server insists on it.
# Up to 3 redirects are followed. HTTPS is deliberately NOT implemented
# in v0.1 (see README, honest limits).
#
# DOCTRINE: GET only. The fetcher never submits a form, never sends a
# body, never carries a cookie. It reads public pages; it does not knock
# twice, log in, or pretend to be a browser.
# ============================================================================

import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from .socks5 import connect_via_socks5

MAX_BODY = 2 * 1024 * 1024  # a page, not a payload: 2 MiB is the ceiling


class FetchError(Exception):
    pass


def _read_http_response(sock):
    """MECHANISM: read status line + headers, then the body to EOF,
    de-chunking if the server used chunked transfer-encoding."""
    raw = b""
    while b"\r\n\r\n" not in raw:
        chunk = sock.recv(65536)
        if not chunk:
            raise FetchError("connection closed before headers completed")
        raw += chunk
        if len(raw) > 65536:
            raise FetchError("header block unreasonably large")
    head, _, rest = raw.partition(b"\r\n\r\n")
    lines = head.decode("iso-8859-1").split("\r\n")
    parts = lines[0].split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise FetchError(f"malformed status line: {lines[0]!r}")
    status = int(parts[1])
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    body = rest
    while len(body) <= MAX_BODY:
        chunk = sock.recv(65536)
        if not chunk:
            break
        body += chunk
    body = body[:MAX_BODY]
    if headers.get("transfer-encoding", "").lower() == "chunked":
        body = _dechunk(body)
    return status, headers, body


def _dechunk(body):
    out, pos = b"", 0
    while True:
        end = body.find(b"\r\n", pos)
        if end == -1:
            break
        try:
            size = int(body[pos:end].split(b";")[0].strip(), 16)
        except ValueError:
            break
        if size == 0:
            break
        out += body[end + 2:end + 2 + size]
        pos = end + 2 + size + 2
    return out


def fetch_http(url, proxy=None, timeout=30.0, _redirects=3):
    """MECHANISM: one GET. proxy=None means a direct connection (the
    local fixture/test mode); proxy=(host, port) means a SOCKS5 tunnel.
    Returns (status, headers, body_bytes)."""
    parts = urlsplit(url)
    if parts.scheme != "http":
        raise FetchError(f"v0.1 fetches plain HTTP only, got: {url}")
    host = parts.hostname
    port = parts.port or 80
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    if proxy is None:
        sock = socket.create_connection((host, port), timeout=timeout)
    else:
        sock = connect_via_socks5(proxy[0], proxy[1], host, port,
                                   timeout=timeout)
    try:
        request = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
                   f"User-Agent: vates-stratorvm/0.1 (research crawler)\r\n"
                   f"Accept: text/html\r\nConnection: close\r\n\r\n")
        sock.sendall(request.encode("utf-8"))
        status, headers, body = _read_http_response(sock)
    finally:
        sock.close()
    if status in (301, 302, 303, 307, 308) and "location" in headers:
        if _redirects <= 0:
            raise FetchError("redirect limit reached")
        return fetch_http(urljoin(url, headers["location"]),
                          proxy=proxy, timeout=timeout,
                          _redirects=_redirects - 1)
    return status, headers, body


class _PageParser(HTMLParser):
    """MECHANISM: one pass over the document collecting three things —
    the <title>, the visible text (script/style bodies excluded), and
    every <a href>. Nothing else is kept."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.text_parts = []
        self.links = []
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag in ("script", "style"):
            self._skip_depth += 1
        elif tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.links.append(v)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
        self.text_parts.append(data)


def extract_page(html_text, base_url):
    """MECHANISM: parse a page into (title, text, absolute_links).
    Whitespace is collapsed so the full-text index stores prose, not
    layout. Links are resolved against the page URL; fragments drop."""
    parser = _PageParser()
    parser.feed(html_text)
    title = " ".join(" ".join(parser.title_parts).split())
    text = " ".join(" ".join(parser.text_parts).split())
    links = []
    for href in parser.links:
        absolute = urljoin(base_url, href).split("#")[0]
        if absolute.startswith("http://") or absolute.startswith("https://"):
            links.append(absolute)
    return title, text, links
