import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["VERCEL"] = "1"

from businessflow_ai.api import app

# Expose app for Vercel Serverless Function
handler = app
