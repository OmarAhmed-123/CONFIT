import sqlite3
import os

DB_PATH = r'e:\CONFIT\backend\confit.db'
OUTPUT_PATH = r'e:\CONFIT\backend\db_status.txt'

def main():
    with open(OUTPUT_PATH, 'w') as f:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if social_posts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='social_posts'")
        result = cursor.fetchone()
        f.write(f"social_posts exists: {result is not None}\n\n")
        
        if result:
            cursor.execute('PRAGMA table_info(social_posts)')
            f.write("Columns in social_posts:\n")
            for row in cursor.fetchall():
                f.write(f"  {row}\n")
        
        conn.close()
        f.write("\nDone.\n")
    
    print("Output written to db_status.txt")

if __name__ == '__main__':
    main()
