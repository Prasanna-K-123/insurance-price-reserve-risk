from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def configuration():
    return json.loads((ROOT / "config.json").read_text())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash_fraction(identifier, namespace, seed):
    message = f"{namespace}:{seed}:{identifier}".encode()
    return int.from_bytes(hashlib.sha256(message).digest()[:8], "big") / 2**64


def split_name(identifier, namespace, seed, first_fraction, second_fraction=0.0):
    fraction = hash_fraction(identifier, namespace, seed)
    if namespace == "pricing":
        return "train" if fraction < first_fraction else (
            "development" if fraction < first_fraction + second_fraction else "test"
        )
    return "development" if fraction < first_fraction else "test"


def split_digest(identifiers, assignments):
    pairs = sorted(zip(map(str, identifiers), map(str, assignments)))
    return hashlib.sha256(json.dumps(pairs, separators=(",", ":")).encode()).hexdigest()


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def provenance():
    return {
        "config_sha256": sha256(ROOT / "config.json"),
        "protocol_sha256": sha256(ROOT / "docs/PROTOCOL.md"),
        "protocol_commit": "c0722d07944037c8cc30e1f315b9b5ef11847cf8",
    }
