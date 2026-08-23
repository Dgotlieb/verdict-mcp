"""Failure fingerprinting.

A fingerprint is a stable hash of a *normalized* failure signature, so the
same logical failure hashes identically across runs even when volatile
details (addresses, tmp paths, timings, ids) differ. Fingerprints power
`history` — the "did this failure exist before my change?" answer.
"""

from __future__ import annotations

import hashlib
import re

_HEX_ADDR = re.compile(r"0x[0-9a-fA-F]+")
_TMP_PATH = re.compile(r"/(?:tmp|var/folders)/[^\s'\"]+")
_LONG_NUM = re.compile(r"\b\d{4,}\b")
_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_WS = re.compile(r"\s+")
_DURATION = re.compile(r"\b\d+(\.\d+)?\s*(s|ms|us|seconds?|milliseconds?)\b")
_LINE_REF = re.compile(r"(:|, line )\d+")


def normalize(message: str) -> str:
    """Collapse volatile tokens so equivalent failures normalize identically."""
    msg = message.strip()
    msg = _UUID.sub("<uuid>", msg)
    msg = _HEX_ADDR.sub("<addr>", msg)
    msg = _TMP_PATH.sub("<tmp>", msg)
    msg = _DURATION.sub("<duration>", msg)
    msg = _LINE_REF.sub(r"\1<line>", msg)
    msg = _LONG_NUM.sub("<n>", msg)
    msg = _WS.sub(" ", msg)
    return msg


def fingerprint(check_id: str, error_type: str, message: str) -> str:
    """Stable 16-hex-char fingerprint for a failure.

    Includes the check id (a test that fails and a different test failing the
    same way are different facts) plus normalized error type and message.
    Deliberately excludes line numbers: refactors move code, the failure stays.
    """
    basis = "\x1f".join([check_id, error_type.strip(), normalize(message)])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
