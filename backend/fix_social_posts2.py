"""Fix social_posts table by recreating it with correct schema."""
import sqlite3
import os

DB_PATH = r'e:\CONFIT\backend\confit.db'
OUTPUT_PATH = r'e:\CONFIT\backend\fix_result.txt'

def fix():
    with open(OUTPUT_PATH, 'w') as log:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check current state
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='social_posts'")
        exists = cursor.fetchone()
        
        if exists:
            # Get current columns
            cursor.execute('PRAGMA table_info(social_posts)')
            cols = [row[1] for row in cursor.fetchall()]
            log.write(f"Current columns: {cols}\n")
            
            # Check if user_id exists
            if 'user_id' not in cols:
                log.write("user_id column missing - recreating table...\n")
                
                # Drop and recreate
                cursor.execute("DROP TABLE IF EXISTS social_posts")
                log.write("Dropped social_posts table\n")
        
        # Create table with correct schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_posts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                outfit_id TEXT,
                caption TEXT,
                hashtags TEXT DEFAULT '[]',
                image_urls TEXT NOT NULL DEFAULT '[]',
                video_url TEXT,
                post_type TEXT NOT NULL DEFAULT 'outfit',
                visibility TEXT NOT NULL DEFAULT 'public',
                location TEXT,
                tags TEXT DEFAULT '[]',
                is_featured INTEGER NOT NULL DEFAULT 0,
                is_archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        log.write("Created social_posts table with correct schema\n")
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_user_id ON social_posts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_visibility ON social_posts(visibility)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_created_at ON social_posts(created_at)")
        
        conn.commit()
        
        # Verify
        cursor.execute('PRAGMA table_info(social_posts)')
        cols = cursor.fetchall()
        log.write(f"\nNew columns: {[c[1] for c in cols]}\n")
        
        conn.close()
        log.write("\nDone! Restart the backend server.\n")

if __name__ == '__main__':
    fix()
