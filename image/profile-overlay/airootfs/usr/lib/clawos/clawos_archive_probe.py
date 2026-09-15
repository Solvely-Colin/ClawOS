"""Read-only reachability probe for the pinned Arch package snapshot."""

import datetime
from pathlib import Path
import re
import subprocess


VERSIONS_ENV = Path("/etc/clawos/versions.env")
SNAPSHOT_PATTERN = re.compile(r"[0-9]{4}/[0-9]{2}/[0-9]{2}")
ARCHIVE_HOST = "archive.archlinux.org"


def pinned_snapshot(path=VERSIONS_ENV):
    """Return the one valid ARCH_SNAPSHOT value; reject ambiguity or drift."""
    values = []
    for line in Path(path).read_text().splitlines():
        if line.startswith("ARCH_SNAPSHOT="):
            values.append(line.partition("=")[2])
    if len(values) != 1 or not SNAPSHOT_PATTERN.fullmatch(values[0]):
        raise ValueError("Pinned Arch snapshot configuration is invalid")
    datetime.date.fromisoformat(values[0].replace("/", "-"))
    return values[0]


def archive_url(snapshot):
    return f"https://{ARCHIVE_HOST}/repos/{snapshot}/core/os/x86_64/core.db"


def probe_archive(path=VERSIONS_ENV, runner=subprocess.run):
    """HEAD the exact pinned database with curl's ten-second deadline."""
    try:
        snapshot = pinned_snapshot(path)
    except (OSError, ValueError):
        return {
            "reachable": False, "snapshot": None, "url": None,
            "reason": "Pinned archive configuration is unavailable.",
        }
    url = archive_url(snapshot)
    command = [
        "/usr/bin/curl", "--head", "--silent", "--show-error",
        "--max-time", "10", "--output", "/dev/null",
        "--write-out", "%{http_code}", "--", url,
    ]
    try:
        result = runner(command, capture_output=True, text=True, timeout=12, check=False)
    except (OSError, subprocess.SubprocessError):
        return {
            "reachable": False, "snapshot": snapshot, "url": url,
            "reason": "The archive check could not complete within 10 seconds.",
        }
    code = result.stdout.strip()
    if result.returncode == 0 and code == "200":
        return {
            "reachable": True, "snapshot": snapshot, "url": url,
            "reason": "Pinned package archive is reachable.",
        }
    if result.returncode in (5, 6):
        reason = "The archive hostname could not be resolved. Check DNS or captive-portal sign-in."
    elif result.returncode == 7:
        reason = "The archive connection was refused or the network is unreachable."
    elif result.returncode == 28:
        reason = "The archive did not answer within 10 seconds."
    elif code.startswith("3"):
        reason = f"The archive returned HTTP {code}; a captive portal or proxy may be intercepting HTTPS."
    elif code and code != "000":
        reason = f"The pinned archive returned HTTP {code}."
    else:
        reason = "The pinned package archive is unreachable over HTTPS."
    return {"reachable": False, "snapshot": snapshot, "url": url, "reason": reason}
