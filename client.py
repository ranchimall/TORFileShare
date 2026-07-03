"""Talks to the peer's hidden service over Tor's SOCKS5 proxy."""
import os
from urllib.parse import quote

import requests


def _proxies(socks_port):
    proxy = f"socks5h://127.0.0.1:{socks_port}"
    return {"http": proxy, "https": proxy}


def _quote_relpath(relative_path):
    """Percent-encode each path segment individually so subfolder slashes
    survive as URL path separators (e.g. photos/trip/img1.jpg)."""
    return "/".join(quote(part, safe="") for part in relative_path.split("/"))


def get_remote_list(peer_onion, socks_port, timeout=30):
    url = f"http://{peer_onion}/list"
    resp = requests.get(url, proxies=_proxies(socks_port), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def push_file(peer_onion, socks_port, filepath, relative_path, timeout=180):
    url = f"http://{peer_onion}/file/{_quote_relpath(relative_path)}"
    with open(filepath, "rb") as f:
        data = f.read()
    resp = requests.post(url, data=data, proxies=_proxies(socks_port), timeout=timeout)
    resp.raise_for_status()


def download_file(peer_onion, socks_port, relative_path, dest_path, timeout=180):
    url = f"http://{peer_onion}/file/{_quote_relpath(relative_path)}"
    resp = requests.get(url, proxies=_proxies(socks_port), timeout=timeout)
    resp.raise_for_status()
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    tmp = dest_path + ".part"
    with open(tmp, "wb") as f:
        f.write(resp.content)
    os.replace(tmp, dest_path)
