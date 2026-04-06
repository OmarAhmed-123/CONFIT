#!/usr/bin/env python3
"""Test that the schema fix works correctly."""
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3

# Check database before fix
print("=== BEFORE FIX ===")
conn = sqlite3.connect('confit.db')
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='social_posts'")
if c.fetchone():
    c.execute('PRAGMA table_info(social_posts)')
    cols = [r[1] for r in c.fetchall()]
    print(f"social_posts columns: {cols}")
    print(f"Has user_id: {'user_id' in cols}")
else:
    print("social_posts table does not exist")

conn.close()

# Run the fix
print("\n=== RUNNING FIX ===")
from database.session import init_db
init_db()
print("init_db() completed")

# Check database after fix
print("\n=== AFTER FIX ===")
conn = sqlite3.connect('confit.db')
c = conn.cursor()

c.execute('PRAGMA table_info(social_posts)')
cols = [r[1] for r in c.fetchall()]
print(f"social_posts columns: {cols}")
print(f"Has user_id: {'user_id' in cols}")

c.execute('PRAGMA table_info(social_votes)')
cols = [r[1] for r in c.fetchall()]
print(f"social_votes columns: {cols}")

conn.close()

print("\n=== SUCCESS ===")
