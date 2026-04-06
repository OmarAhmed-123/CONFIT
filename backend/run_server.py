#!/usr/bin/env python
"""Start backend server."""
import os
import sys

# Ensure we're in the backend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from main import app

if __name__ == "__main__":
    print("Starting CONFIT Backend Server...")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
