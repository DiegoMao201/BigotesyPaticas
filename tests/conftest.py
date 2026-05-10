"""Pytest config — añade la raíz del repo al sys.path para imports limpios."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
