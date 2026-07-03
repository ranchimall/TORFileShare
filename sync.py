"""Two mechanisms keep the folders in sync:

1. PushHandler (watchdog) -- fires immediately when a file is created or
   changed anywhere under the shared folder (including subfolders),
   pushing it to the peer right away.
2. reconcile_once / start_periodic_sync -- a periodic full comparison in
   both directions, so anything missed (e.g. peer was offline) eventually
   catches up.

A small "recently_received" dict is used to stop a file we just pulled
from the peer from immediately being pushed straight back at them.
Files/folders are matched by relative path (e.g. "photos/trip/img1.jpg").
"""
import os
import time
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from utils import list_shared_files
import client


def _to_relpath(shared_dir, path):
    return os.path.relpath(path, shared_dir).replace(os.sep, "/")


def _is_hidden(relative_path):
    return any(part.startswith(".") for part in relative_path.split("/"))


class PushHandler(FileSystemEventHandler):
    def __init__(self, shared_dir, get_peer, socks_port, recently_received, cooldown=5):
        self.shared_dir = shared_dir
        self.get_peer = get_peer
        self.socks_port = socks_port
        self.recently_received = recently_received
        self.cooldown = cooldown

    def _maybe_push(self, path):
        if not os.path.isfile(path):
            return
        if path.endswith(".part"):
            return
        rel = _to_relpath(self.shared_dir, path)
        if _is_hidden(rel):
            return
        peer = self.get_peer()
        if not peer:
            return
        recv_time = self.recently_received.get(rel)
        if recv_time and abs(os.path.getmtime(path) - recv_time) < self.cooldown:
            return  # we just wrote this ourselves after pulling it, skip echo
        try:
            client.push_file(peer, self.socks_port, path, rel)
            print(f"[push] sent {rel} to peer")
        except Exception as e:
            print(f"[push] failed to send {rel}: {e}")

    def on_created(self, event):
        if not event.is_directory:
            self._maybe_push(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._maybe_push(event.src_path)


def start_watcher(shared_dir, get_peer, socks_port, recently_received):
    handler = PushHandler(shared_dir, get_peer, socks_port, recently_received)
    observer = Observer()
    observer.schedule(handler, shared_dir, recursive=True)
    observer.start()
    return observer


def _rel_to_path(shared_dir, relative_path):
    return os.path.join(shared_dir, *relative_path.split("/"))


def reconcile_once(shared_dir, peer, socks_port, recently_received):
    try:
        remote_files = client.get_remote_list(peer, socks_port)
    except Exception as e:
        print(f"[sync] could not reach peer: {e}")
        return

    local_files = list_shared_files(shared_dir)

    # Pull anything remote we don't have (or that differs).
    for rel, meta in remote_files.items():
        local_meta = local_files.get(rel)
        if local_meta is None or local_meta["sha256"] != meta["sha256"]:
            dest = _rel_to_path(shared_dir, rel)
            try:
                client.download_file(peer, socks_port, rel, dest)
                recently_received[rel] = os.path.getmtime(dest)
                print(f"[pull] downloaded {rel} from peer")
            except Exception as e:
                print(f"[pull] failed to download {rel}: {e}")

    # Push anything local the peer doesn't have (or that differs).
    for rel, meta in local_files.items():
        remote_meta = remote_files.get(rel)
        if remote_meta is None or remote_meta["sha256"] != meta["sha256"]:
            path = _rel_to_path(shared_dir, rel)
            try:
                client.push_file(peer, socks_port, path, rel)
                print(f"[push] sent {rel} to peer (reconcile)")
            except Exception as e:
                print(f"[push] failed to send {rel} (reconcile): {e}")


def start_periodic_sync(shared_dir, get_peer, socks_port, recently_received, interval=60):
    def loop():
        while True:
            peer = get_peer()
            if peer:
                reconcile_once(shared_dir, peer, socks_port, recently_received)
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
