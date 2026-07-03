"""Proxy link builder — constructs ``tg://proxy`` URLs.

Per INV-DOMAIN, proxy links must use domain names (never raw IPs) in the
``server=`` field so that links survive server migration. The domain is
the entry server FQDN, not an IP address.
"""

from __future__ import annotations


def build_proxy_link(server: str, port: int, secret: str) -> str:
    """Build a ``tg://proxy`` link from server, port, and secret.

    The resulting link has the format::

        tg://proxy?server=<server>&port=<port>&secret=<secret>

    Per INV-DOMAIN, ``server`` must be a domain name (FQDN), not a raw
    IP address. This ensures links survive server migration — when the
    entry server IP changes, the DNS record is updated and existing
    links continue to work.

    Args:
        server: Entry server FQDN (domain name, never a raw IP).
        port: Entry server port (e.g. 443).
        secret: The proxy secret from telemt (returned by
            ``TelemtClient.create_user()``).

    Returns:
        A ``tg://proxy?server=...&port=...&secret=...`` URL string.
    """
    return f"tg://proxy?server={server}&port={port}&secret={secret}"
