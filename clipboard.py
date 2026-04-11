import shutil
import subprocess
import time
from typing import Tuple


def _ensure_wl_clipboard():
    if not (shutil.which('wl-copy') and shutil.which('wl-paste')):
        raise RuntimeError('wl-copy/wl-paste not found; Wayland clipboard tools required')


def copy(string: str, target: str = None) -> subprocess.CompletedProcess:
    """Copy `string` to the Wayland clipboard using `wl-copy`.
    Pass `target` as the MIME type via `--type` when provided.
    """
    _ensure_wl_clipboard()
    cmd = ['wl-copy']
    if target is not None:
        cmd += ['--type', target]
    result = subprocess.run(cmd, input=string, text=True)
    time.sleep(0.5)  # Wait a moment for clipboard to be populated
    return result


def get(target: str = None) -> str:
    """Read clipboard contents using `wl-paste`. If `target` is supplied,
    return the clipboard for that MIME type if available, otherwise return
    an empty string.
    """
    _ensure_wl_clipboard()
    if target is not None:
        p = subprocess.run(['wl-paste', '--list-types'], stdout=subprocess.PIPE, text=True)
        types = [t.strip() for t in p.stdout.splitlines()]
        if any(target in t for t in types):
            p2 = subprocess.run(['wl-paste', '--no-newline', '--type', target], stdout=subprocess.PIPE, text=True)
            return p2.stdout.strip()
        return ''

    p = subprocess.run(['wl-paste', '--no-newline'], stdout=subprocess.PIPE, text=True)
    return p.stdout.strip()


def has_target(target: str) -> Tuple[bool, str]:
    """Return (supported, detail) by querying `wl-paste --list-types`.
    """
    _ensure_wl_clipboard()
    p = subprocess.run(['wl-paste', '--list-types'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ok = any(target in t for t in p.stdout.splitlines())
    return ok, p.stdout
