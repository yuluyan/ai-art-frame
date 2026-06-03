import hashlib
import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAIN_SCRIPT = os.path.join(REPO_ROOT, "src", "main.py")
# Runtime state the frame writes at startup/use. It is snapshotted and restored
# around the pull so a fast-forward is never blocked and the device keeps its
# settings + image history — including the one-time pull that de-tracks them.
RUNTIME_FILES = ("configs.json", "imgs/records.json")


def _run(cmd, timeout=600):
    return subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout
    )


def _backup_runtime_files():
    backups = {}
    for rel in RUNTIME_FILES:
        path = os.path.join(REPO_ROOT, *rel.split("/"))
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    backups[path] = f.read()
            except Exception:
                pass
    return backups


def _restore_runtime_files(backups):
    for path, data in backups.items():
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
        except Exception:
            pass


def _file_hash(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _resolve_uv():
    """Find the uv executable; under systemd the user PATH may be missing."""
    uv = shutil.which("uv")
    if uv:
        return uv
    base = os.path.join(os.path.expanduser("~"), ".local", "bin", "uv")
    for candidate in (base, base + ".exe"):
        if os.path.exists(candidate):
            return candidate
    return None


def perform_sync(status=print) -> dict:
    """Pull the latest code; if uv.lock changed, run `uv sync`.

    Returns {ok, updated, deps_changed, message}. Never raises.
    """
    result = {"ok": False, "updated": False, "deps_changed": False, "message": ""}
    try:
        status("Checking git...")
        head_before = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
        lock_path = os.path.join(REPO_ROOT, "uv.lock")
        lock_before = _file_hash(lock_path)

        # Snapshot runtime data, clear any tracked edits so the pull can
        # fast-forward, then write the snapshot back afterwards.
        backups = _backup_runtime_files()
        for rel in RUNTIME_FILES:
            _run(["git", "checkout", "--", rel])

        status("Pulling updates...")
        pull = _run(["git", "pull", "--ff-only"])
        _restore_runtime_files(backups)
        if pull.returncode != 0:
            result["message"] = "git pull failed:\n" + (pull.stderr or pull.stdout).strip()
            return result

        head_after = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
        result["updated"] = bool(head_before) and (head_before != head_after)

        if not result["updated"]:
            result["ok"] = True
            result["message"] = "Already up to date."
            return result

        if lock_before != _file_hash(lock_path):
            uv = _resolve_uv()
            if uv is None:
                result["message"] = "Updated, but 'uv' not found to install new dependencies."
                return result
            status("Installing dependencies...")
            sync = _run([uv, "sync"])
            if sync.returncode != 0:
                result["message"] = "uv sync failed:\n" + (sync.stderr or sync.stdout).strip()
                return result
            result["deps_changed"] = True

        result["ok"] = True
        result["message"] = "Updated. Restarting..."
        return result
    except Exception as e:
        result["message"] = f"Sync error: {e}"
        return result


def restart_process():
    """Replace the current process with a fresh run of the app.

    Under a systemd supervisor (INVOCATION_ID set) exit cleanly and let the unit
    relaunch with a fresh environment; otherwise re-exec in place. The caller
    must release resources (mic, window) first. An absolute path to main.py keeps
    `src/` on sys.path so the cwd-relative imports still resolve.
    """
    if os.environ.get("INVOCATION_ID"):
        sys.exit(0)
    os.execv(sys.executable, [sys.executable, MAIN_SCRIPT, *sys.argv[1:]])
