"""Allow ``python -m github_achievements_progress``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
