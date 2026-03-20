"""Validate locale key consistency.

Usage:
    python scripts/check_locales.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Set


LOCALES_PATH = Path(__file__).resolve().parents[1] / "locales.json"


def load_locales(path: Path) -> Dict[str, Dict[str, str]]:
    """Load and type-validate locale JSON structure."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("locales.json root must be an object")

    normalized: Dict[str, Dict[str, str]] = {}
    for locale, mapping in data.items():
        if not isinstance(locale, str):
            raise ValueError("locale keys must be strings")
        if not isinstance(mapping, dict):
            raise ValueError(f"locale '{locale}' must map to an object")
        casted: Dict[str, str] = {}
        for k, v in mapping.items():
            if not isinstance(k, str):
                raise ValueError(f"locale '{locale}' has non-string key")
            if not isinstance(v, str):
                raise ValueError(f"locale '{locale}' key '{k}' must map to string")
            casted[k] = v
        normalized[locale] = casted

    return normalized


def sorted_keys(mapping: Dict[str, str]) -> Set[str]:
    """Return locale key set for comparison."""
    return set(mapping.keys())


def main() -> int:
    """Run locale consistency checks and return an exit code."""
    if not LOCALES_PATH.exists():
        print(f"ERROR: locales file not found: {LOCALES_PATH}")
        return 1

    try:
        locales = load_locales(LOCALES_PATH)
    except Exception as e:
        print(f"ERROR: failed to parse locales.json: {e}")
        return 1

    if not locales:
        print("ERROR: no locale entries found")
        return 1

    base_locale = "en" if "en" in locales else next(iter(locales.keys()))
    base_keys = sorted_keys(locales[base_locale])

    mismatch_found = False
    for locale, mapping in locales.items():
        keys = sorted_keys(mapping)
        missing = sorted(base_keys - keys)
        extra = sorted(keys - base_keys)
        if missing or extra:
            mismatch_found = True
            print(f"Locale '{locale}' mismatch compared to '{base_locale}':")
            if missing:
                print("  Missing keys:")
                for key in missing:
                    print(f"    - {key}")
            if extra:
                print("  Extra keys:")
                for key in extra:
                    print(f"    + {key}")

    if mismatch_found:
        return 1

    print(f"OK: locale keys are consistent across {len(locales)} locales.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
