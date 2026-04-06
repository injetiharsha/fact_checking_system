import os
import sys

# Add repo root to path
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from main import app

# Vercel ASGI handler
handler = app