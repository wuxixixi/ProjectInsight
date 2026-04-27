#!/usr/bin/env python3
"""Compatibility wrapper for frontend-only deployment."""

import sys

from deploy import main


if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--frontend-only", *sys.argv[1:]]
    raise SystemExit(main())
