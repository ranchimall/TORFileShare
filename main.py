"""Tor-based two-way file sync.

Run this exact same script on both machines. Each side:
  1. Launches its own Tor process with an ephemeral hidden service.
  2. Prints its .onion address -- send this to the other person over any
     secure channel you like (Signal, in person, etc). It is not a secret
     key, but it does let whoever has it read/write your shared folder,
     so don't post it publicly.
  3. Serves its shared folder locally, reachable only via that .onion address.
  4. Watches its shared folder and pushes new/changed files to the peer.
  5. Periodically reconciles both folders so nothing is missed.

Usage:
    First run on each side (no peer known yet):
        python main.py --shared-dir ./shared

    It will print something like:
        [tor] your onion address: abcdefgh...ijkl.onion

    Exchange addresses with your peer, then either restart with:
        python main.py --shared-dir ./shared --peer <their onion address>
    or, while it's running, just write the address into:
        ./tor_data/peer.txt
    (it's re-read automatically, no restart needed)
"""
import argparse
import os
import sys
import time

from tor_service import start_tor_hidden_service
from server import start_server
from sync import start_watcher, start_periodic_sync


def read_peer_file(path):
    if os.path.isfile(path):
        with open(path) as f:
            value = f.read().strip()
            return value or None
    return None


def main():
    parser = argparse.ArgumentParser(description="Tor-based two-way file sync")
    parser.add_argument("--shared-dir", default="./shared", help="Folder to sync")
    parser.add_argument("--data-dir", default="./tor_data", help="Folder for Tor/hidden-service state")
    parser.add_argument("--http-port", type=int, default=8000, help="Local HTTP server port")
    parser.add_argument("--socks-port", type=int, default=9050, help="Local Tor SOCKS port")
    parser.add_argument("--peer", default=None, help="Peer's .onion address")
    parser.add_argument("--sync-interval", type=int, default=60, help="Seconds between full reconciliations")
    args = parser.parse_args()

    os.makedirs(args.shared_dir, exist_ok=True)
    os.makedirs(args.data_dir, exist_ok=True)

    peer_file = os.path.join(args.data_dir, "peer.txt")
    if args.peer:
        with open(peer_file, "w") as f:
            f.write(args.peer.strip())

    print("[tor] starting Tor and creating hidden service (can take 10-60s the first time)...")
    tor_process, onion_address = start_tor_hidden_service(args.data_dir, args.socks_port, args.http_port)
    print(f"[tor] your onion address: {onion_address}")
    print("[tor] share this with your peer over a secure channel.")

    recently_received = {}
    start_server(args.shared_dir, args.http_port, recently_received)
    print(f"[server] serving {args.shared_dir} on 127.0.0.1:{args.http_port} (reachable via Tor only)")

    def get_peer():
        return read_peer_file(peer_file)

    start_watcher(args.shared_dir, get_peer, args.socks_port, recently_received)
    start_periodic_sync(args.shared_dir, get_peer, args.socks_port, recently_received, args.sync_interval)

    peer = get_peer()
    if peer:
        print(f"[sync] peer set to {peer}, reconciling every {args.sync_interval}s")
    else:
        print(f"[sync] no peer set yet. Once you have their onion address, write it into:")
        print(f"       {peer_file}")
        print(f"       (or restart this script with --peer <onion_address>)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[main] shutting down...")
        tor_process.kill()
        sys.exit(0)


if __name__ == "__main__":
    main()
