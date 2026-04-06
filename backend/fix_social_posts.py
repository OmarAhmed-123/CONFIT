"""Fix social_posts table by recreating it with correct schema."""
import sqlite3
import os

DB_PATH = r'e:\CONFIT\backend\confit.db'

def fix():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check current state
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='social_posts'")
    exists = cursor.fetchone()
    
    if exists:
        # Get current columns
        cursor.execute('PRAGMA table_info(social_posts)')
        cols = [row[1] for row in cursor.fetchall()]
        print(f"Current columns: {cols}")
        
        # Check if user_id exists
        if 'user_id' not in cols:
            print("user_id column missing - recreating table...")
            
            # Backup existing data
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='social_posts'")
            old_schema = cursor.fetchone()
            print(f"Old schema: {old_schema}")
            
            # Drop and recreate
            cursor.execute("DROP TABLE IF EXISTS social_posts")
            print("Dropped social_posts table")
    
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
    print("Created social_posts table with correct schema")
    
    # Create index
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_user_id ON social_posts(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_visibility ON social_posts(visibility)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_created_at ON social_posts(created_at)")
    
    conn.commit()
    
    # Verify
    cursor.execute('PRAGMA table_info(social_posts)')
    cols = cursor.fetchall()
    print(f"\nNew columns: {[c[1] for c in cols]}")
    
    conn.close()
    print("\nDone! Restart the backend server.")

if __name__ == '__main__':
    fix()
