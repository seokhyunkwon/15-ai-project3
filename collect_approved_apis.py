from __future__ import annotations

import json

import collector


def main() -> None:
    results = collector.collect_approved_api_bundle()
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
