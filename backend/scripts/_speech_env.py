"""
Shared setup for the speech verification scripts.

Handles the three things every one of them needs before it can talk to Azure:
the credentials out of ``backend/.env``, the GStreamer decoder on PATH, and a
scratch directory for generated audio. Kept separate so the scripts
themselves stay about what they are checking.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

REPO_ROOT = BACKEND_DIR.parent

# Generated audio lives outside the repository. It is large, binary, and
# recreatable in seconds, so there is no reason to carry it in git.
FIXTURE_DIR = Path(tempfile.gettempdir()) / "interviewmirror-speech-fixtures"


def _gstreamer_candidates() -> list[Path]:
    """Where the GStreamer runtime usually lands on Windows."""

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")

    roots = [
        Path(local_app_data) / "Programs" / "gstreamer",
        Path(program_files) / "gstreamer",
        Path("C:/gstreamer"),
    ]

    return [
        root / "1.0" / flavour / "bin"
        for root in roots
        if str(root)
        for flavour in ("msvc_x86_64", "mingw_x86_64")
    ]


def load_env() -> None:
    """Load backend/.env into os.environ without overwriting real env vars."""

    env_file = BACKEND_DIR / ".env"

    if not env_file.is_file():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def add_gstreamer_to_path() -> bool:
    """
    Put GStreamer on PATH for this process and report whether it is there.

    Azure Speech needs it to decode anything that is not WAV, which includes
    both the browser's webm/opus and the mp3 fixtures.
    """

    if shutil.which("gst-launch-1.0"):
        return True

    for candidate in _gstreamer_candidates():
        if (candidate / "gst-launch-1.0.exe").is_file():
            os.environ["PATH"] = (
                f"{candidate}{os.pathsep}{os.environ.get('PATH', '')}"
            )
            return True

    return False


def gstreamer_launcher() -> Path | None:
    """Absolute path to gst-launch-1.0, for scripts that shell out to it."""

    found = shutil.which("gst-launch-1.0")

    if found:
        return Path(found)

    for candidate in _gstreamer_candidates():
        launcher = candidate / "gst-launch-1.0.exe"

        if launcher.is_file():
            return launcher

    return None


def speech_credentials() -> tuple[str, str]:
    """Return (key, region), exiting with a clear message if unconfigured."""

    load_env()

    key = os.environ.get("AZURE_SPEECH_KEY", "")
    region = os.environ.get("AZURE_SPEECH_REGION", "")

    if not key or not region:
        raise SystemExit(
            "AZURE_SPEECH_KEY / AZURE_SPEECH_REGION not found in "
            f"{BACKEND_DIR / '.env'} or the environment."
        )

    return key, region


def import_app_modules() -> None:
    """Make `app.*` importable when running these as plain scripts."""

    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))


def setup() -> tuple[str, str, bool]:
    """Do everything: returns (key, region, gstreamer_available)."""

    key, region = speech_credentials()
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    return key, region, add_gstreamer_to_path()
