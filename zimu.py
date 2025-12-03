import sys
from pathlib import Path

# Ensure src/ is on sys.path for imports
ROOT = Path(__file__).parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cli import main  # now import from src package root

if __name__ == "__main__":
    sys.exit(main())
