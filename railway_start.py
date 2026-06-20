from __future__ import annotations

import os
import sys

import uvicorn


def main() -> None:
    port_value = os.getenv("PORT", "8000")
    try:
        port = int(port_value)
    except ValueError:
        print(f"Invalid PORT value: {port_value!r}. Falling back to 8000.", file=sys.stderr)
        port = 8000

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
