"""Temporary files of the atomic writes into the game's user folder, kept outside it.

The game watches its user folder: every file created or changed there is an onFileChanged event, handled in Lua by
every loaded extension, and the engine's FileWatchers took up to ~1 s in a frame during a 100 mph drive (2026-10-17).
A write as "<path>.tmp" then os.replace() made two events per tile file (3,220 in a 3 km drive, 1,079 of them .tmp).
tmp_for(path) puts the temporary file in "beamngEarth_staging" next to the user folder (the same disk: the rename stays
atomic), so only the finished file shows up. Paths outside a user folder's "temp" (the download cache) keep
"<path>.tmp". Pure but for creating that folder.
"""
import itertools
import os
import threading

STAGING = "beamngEarth_staging"
FILE_ATTRIBUTE_TEMPORARY = 0x100
_made = set()
_lock = threading.Lock()
_serial = itertools.count()


SWEEP_AGE_S = 3600


def mark_temporary(path, create=False):
    """On Windows, set FILE_ATTRIBUTE_TEMPORARY (0x100) on a staged file so the OS cache keeps it in memory."""
    if os.name != "nt":
        return
    try:
        if create and not os.path.exists(path):
            open(path, "wb").close()
        if os.path.exists(path):
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_TEMPORARY)
    except Exception:
        pass


def _sweep(d):
    """Temporary files left by a process that ended mid-write (older than SWEEP_AGE_S), once per process."""
    import shutil
    import time
    now = time.time()
    for name in os.listdir(d):
        p = os.path.join(d, name)
        try:
            if name.endswith(".tmp") and now - os.path.getmtime(p) > SWEEP_AGE_S:
                os.remove(p)
            elif os.path.isdir(p) and now - os.path.getmtime(p) > SWEEP_AGE_S:
                shutil.rmtree(p, ignore_errors=True)
        except OSError:
            pass


def staging_dir(path, sid=None):
    """The staging folder for a file in a user folder's temp tree (or already in staging), or None."""
    p = os.path.abspath(path)
    sep = os.sep
    marker = f"{sep}{STAGING}{sep}"
    j = p.rfind(marker)
    if j > 0:
        base = p[:j + len(sep) + len(STAGING)]
        return os.path.join(base, sid) if sid else base
    if p.endswith(f"{sep}{STAGING}"):
        return os.path.join(p, sid) if sid else p
    i = p.rfind(f"{sep}temp{sep}")
    if i <= 0:
        return None
    user = p[:i]                                        # .../BeamNG.drive/current
    base = os.path.join(os.path.dirname(user), STAGING)
    return os.path.join(base, sid) if sid else base


def session_dir(path, sid=None):
    """The external staging directory (beamngEarth_staging/<sid>/) for a session's master assets, or None."""
    p = os.path.abspath(path)
    sep = os.sep
    if sid is None:
        marker = f"{sep}{STAGING}{sep}"
        j = p.rfind(marker)
        if j > 0:
            rest = p[j + len(marker):].split(sep)
            if rest and rest[0]:
                sid = rest[0]
        else:
            i = p.rfind(f"{sep}temp{sep}")
            if i > 0:
                rest = p[i + len(sep) + 4 + len(sep):].split(sep)
                if len(rest) >= 2 and rest[0].lower() == "beamngearth" and rest[1]:
                    sid = rest[1]
    base = staging_dir(p)
    if base is None:
        return None
    return os.path.join(base, sid) if sid else base


def _ensure_dir(d, sweep=False):
    with _lock:
        known = d in _made
    if not known or not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
        if sweep and not known:
            _sweep(d)
        with _lock:
            _made.add(d)


def master_for(path, sid=None):
    """External staged path (beamngEarth_staging/<sid>/<name>) for a master asset outside the watched userpath."""
    d = session_dir(path, sid=sid)
    if d is None:
        return path
    try:
        _ensure_dir(d)
    except OSError:
        return path
    out = os.path.join(d, os.path.basename(path))
    mark_temporary(out)
    return out


stage_for = master_for


def tmp_for(path):
    """A temporary path to write path's content to before os.replace(tmp, path)."""
    d = staging_dir(path)
    if d is not None:
        try:
            _ensure_dir(d, sweep=True)
        except OSError:
            d = None
    if d is None:
        return path + ".tmp"
    tmp = os.path.join(d, f"{os.getpid()}_{threading.get_ident()}_{next(_serial)}_{os.path.basename(path)}.tmp")
    mark_temporary(tmp, create=True)
    return tmp


def replace(tmp, path):
    """Atomic replace that guarantees the destination folder exists (resilient against game update / temp wipe)."""
    if os.name == "nt" and (STAGING in os.path.abspath(tmp) or STAGING in os.path.abspath(path)):
        mark_temporary(tmp)
    try:
        os.replace(tmp, path)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        os.replace(tmp, path)

