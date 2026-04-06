#!/usr/bin/env python
"""Test script that writes to file."""
import sys
import traceback

with open("E:/CONFIT/backend/test_result.txt", "w") as f:
    try:
        from main import app
        f.write("SUCCESS: FastAPI app loaded\n")
        f.write(f"Title: {app.title}\n")
        f.write(f"Routes: {len([r for r in app.routes])}\n")
        
        from core.config import settings
        f.write(f"Environment: {settings.ENVIRONMENT}\n")
        
        from repositories import UserRepository, ProductRepository
        f.write("Repositories: OK\n")
        
        from schemas import UserCreate, ProductCreate
        f.write("Schemas: OK\n")
        
        from utils import validate_email, utc_now
        f.write("Utils: OK\n")
        
        f.write("\nALL IMPORTS SUCCESSFUL\n")
        
    except Exception as e:
        f.write(f"ERROR: {e}\n")
        traceback.print_exc(file=f)
        sys.exit(1)

sys.exit(0)
