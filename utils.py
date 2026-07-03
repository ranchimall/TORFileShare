"""Small shared helpers used by both the server and the sync logic."""
import hashlib
import os


def sha256_of_file(path, block_size=65536):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            h.update(block)
    return h.hexdigest()


def list_shared_files(shared_dir):
    """Recursively list every regular file under shared_dir.

    Returns {relative_path: {sha256, size, mtime}} where relative_path
    always uses forward slashes (e.g. "photos/trip/img1.jpg"), regardless
    of OS. Skips in-progress ".part" files, dotfiles, and dot-directories
    (like .DS_Store, .git) so junk doesn't get synced.
    """
    files = {}
    for root, dirs, filenames in os.walk(shared_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in filenames:
            if name.endswith(".part") or name.startswith("."):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, shared_dir).replace(os.sep, "/")
            files[rel] = {
                "sha256": sha256_of_file(full),
                "size": os.path.getsize(full),
                "mtime": os.path.getmtime(full),
            }
    return files


def safe_join(shared_dir, relative_path):
    """Resolve relative_path (forward-slash separated) against shared_dir,
    refusing anything that would escape shared_dir (via "..", an absolute
    path, etc). Returns (absolute_filesystem_path, normalized_relative_path).
    Raises ValueError if the path is invalid or would escape."""
    if not relative_path:
        raise ValueError("empty path")

    relative_path = relative_path.replace("\\", "/")
    parts = [p for p in relative_path.split("/") if p not in ("", ".")]

    if not parts or any(p == ".." for p in parts):
        raise ValueError("invalid or path-traversal path")

    full = os.path.join(shared_dir, *parts)
    shared_abs = os.path.abspath(shared_dir)
    full_abs = os.path.abspath(full)

    if full_abs != shared_abs and not full_abs.startswith(shared_abs + os.sep):
        raise ValueError("path escapes shared directory")

    return full_abs, "/".join(parts)
