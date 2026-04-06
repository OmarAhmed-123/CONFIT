#!/usr/bin/env python3
"""Run database schema fix and output results to file."""
import sqlite3
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def main():
    results = []
    
    # Check current state
    conn = sqlite3.connect('confit.db')
    c = conn.cursor()
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='social_posts'")
    exists = c.fetchone()
    
    if exists:
        c.execute('PRAGMA table_info(social_posts)')
        cols = [r[1] for r in c.fetchall()]
        results.append(f"BEFORE: social_posts columns: {cols}")
        results.append(f"BEFORE: Has user_id: {'user_id' in cols}")
    else:
        results.append("BEFORE: social_posts table does not exist")
    
    conn.close()
    
    # Run init_db which includes the fix
    results.append("\nRunning init_db()...")
    from database.session import init_db
    init_db()
    results.append("init_db() completed")
    
    # Check after fix
    conn = sqlite3.connect('confit.db')
    c = conn.cursor()
    
    c.execute('PRAGMA table_info(social_posts)')
    cols = [r[1] for r in c.fetchall()]
    results.append(f"\nAFTER: social_posts columns: {cols}")
    results.append(f"AFTER: Has user_id: {'user_id' in cols}")
    
    c.execute('PRAGMA table_info(social_votes)')
    cols = [r[1] for r in c.fetchall()]
    results.append(f"AFTER: social_votes columns: {cols}")
    
    conn.close()
    
    results.append("\n=== FIX COMPLETE ===")
    
    # Write results
    with open('db_fix_results.txt', 'w') as f:
        f.write('\n'.join(results))
    
    print('\n'.join(results))

if __name__ == '__main__':
    main()
