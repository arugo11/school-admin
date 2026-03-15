from __future__ import annotations

import subprocess
from functools import lru_cache


@lru_cache(maxsize=4)
def azure_cli_key(resource_group: str, account_name: str) -> str | None:
    try:
        result = subprocess.run(
            [
                "az",
                "cognitiveservices",
                "account",
                "keys",
                "list",
                "-g",
                resource_group,
                "-n",
                account_name,
                "--query",
                "key1",
                "-o",
                "tsv",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    key = result.stdout.strip()
    return key or None
