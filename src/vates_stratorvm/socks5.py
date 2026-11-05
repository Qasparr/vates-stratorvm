# ============================================================================
# 93
#
# VATES STRATORVM · socks5.py — a SOCKS5 client written by hand.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Scientific Illuminism — Method of Science, Aim of Religion.
#
# Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All
# Rights Reserved, Without Prejudice.
#
# MECHANISM: RFC 1928, no-authentication method only. The handshake is
# three moves: (1) greeting — version 5, one method offered, method 0
# (no auth); (2) request — CONNECT, with the destination given as a
# DOMAIN NAME (address type 3) so the .onion name is resolved by the Tor
# proxy itself and never leaks to a local resolver; (3) reply — version,
# status, and a bound address whose length depends on its type.
#
# DOCTRINE: ground up means ground up. This file is the whole dependency:
# the stdlib `socket` module and nothing else. No PySocks.
# ============================================================================

import socket
import struct

SOCKS_VERSION = 5
METHOD_NO_AUTH = 0
CMD_CONNECT = 1
ATYP_IPV4 = 1
ATYP_DOMAIN = 3
ATYP_IPV6 = 4

REP_MEANINGS = {
    0: "succeeded",
    1: "general SOCKS server failure",
    2: "connection not allowed by ruleset",
    3: "network unreachable",
    4: "host unreachable",
    5: "connection refused",
    6: "TTL expired",
    7: "command not supported",
    8: "address type not supported",
}


class Socks5Error(Exception):
    """Any failure of the handshake or the reply, stated plainly."""


def parse_reply_header(data):
    """MECHANISM: validate the first four reply bytes (VER, REP, RSV,
    ATYP) and return (rep, atyp). Separated from the socket code so the
    parsing law can be unit-tested without a network."""
    if len(data) < 4:
        raise Socks5Error("reply too short")
    ver, rep, _rsv, atyp = data[0], data[1], data[2], data[3]
    if ver != SOCKS_VERSION:
        raise Socks5Error(f"bad SOCKS version in reply: {ver}")
    return rep, atyp


def bound_address_length(atyp, first_byte=None):
    """MECHANISM: how many bytes follow the reply header for the bound
    address + port. IPv4: 4+2. Domain: 1 length byte, then that many
    bytes, +2. IPv6: 16+2. The domain form needs its length byte read
    first, so it is passed in."""
    if atyp == ATYP_IPV4:
        return 6
    if atyp == ATYP_IPV6:
        return 18
    if atyp == ATYP_DOMAIN:
        if first_byte is None:
            raise Socks5Error("domain bound address needs its length byte")
        return 1 + first_byte + 2
    raise Socks5Error(f"unknown address type in reply: {atyp}")


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise Socks5Error("proxy closed the connection mid-reply")
        buf += chunk
    return buf


def connect_via_socks5(proxy_host, proxy_port, dest_host, dest_port,
                       timeout=30.0):
    """MECHANISM: open a TCP connection to the proxy, perform the
    handshake for (dest_host, dest_port), and return the live socket,
    already tunnelled. The caller speaks plain HTTP over it."""
    sock = socket.create_connection((proxy_host, proxy_port),
                                    timeout=timeout)
    try:
        # (1) Greeting: version 5, one method, no-authentication.
        sock.sendall(bytes([SOCKS_VERSION, 1, METHOD_NO_AUTH]))
        greeting = _recv_exact(sock, 2)
        if greeting[0] != SOCKS_VERSION or greeting[1] != METHOD_NO_AUTH:
            raise Socks5Error("proxy refused the no-auth method")

        # (2) Request: CONNECT with a domain-name address, so name
        # resolution happens at the proxy (the Tor side), never locally.
        host_bytes = dest_host.encode("idna")
        if len(host_bytes) > 255:
            raise Socks5Error("destination host name too long")
        request = (bytes([SOCKS_VERSION, CMD_CONNECT, 0, ATYP_DOMAIN,
                          len(host_bytes)])
                   + host_bytes + struct.pack("!H", dest_port))
        sock.sendall(request)

        # (3) Reply: header, then the bound address at its typed length.
        rep, atyp = parse_reply_header(_recv_exact(sock, 4))
        if atyp == ATYP_DOMAIN:
            first = _recv_exact(sock, 1)
            _recv_exact(sock, bound_address_length(atyp, first[0]) - 1)
        else:
            _recv_exact(sock, bound_address_length(atyp))
        if rep != 0:
            raise Socks5Error(
                f"proxy CONNECT failed: {REP_MEANINGS.get(rep, rep)}")
        return sock
    except Exception:
        sock.close()
        raise
