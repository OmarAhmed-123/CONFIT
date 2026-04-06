"""
Fix SQLite database schema - add missing columns to social_posts table.
This script handles the schema mismatch between models and existing SQLite DB.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'confit.db')

def fix_social_posts_table():
    """Add missing columns to social_posts table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if social_posts table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='social_posts'")
    if not cursor.fetchone():
        print("social_posts table doesn't exist - will be created by SQLAlchemy")
        conn.close()
        return
    
    # Get existing columns
    cursor.execute('PRAGMA table_info(social_posts)')
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"Existing columns in social_posts: {existing_columns}")
    
    # Required columns based on SocialPost model
    required_columns = {
        'id': 'UUID PRIMARY KEY',
        'user_id': 'UUID NOT NULL',
        'outfit_id': 'VARCHAR(64)',
        'caption': 'TEXT',
        'hashtags': 'JSON',
        'image_urls': 'JSON NOT NULL DEFAULT "[]"',
        'video_url': 'VARCHAR(1024)',
        'post_type': 'VARCHAR(32) NOT NULL DEFAULT "outfit"',
        'visibility': 'VARCHAR(32) NOT NULL DEFAULT "public"',
        'location': 'VARCHAR(255)',
        'tags': 'JSON',
        'is_featured': 'BOOLEAN NOT NULL DEFAULT 0',
        'is_archived': 'BOOLEAN NOT NULL DEFAULT 0',
        'created_at': 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP',
        'updated_at': 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP'
    }
    
    # Add missing columns
    columns_added = []
    for col_name, col_def in required_columns.items():
        if col_name not in existing_columns:
            try:
                sql = f'ALTER TABLE social_posts ADD COLUMN {col_name} {col_def}'
                cursor.execute(sql)
                columns_added.append(col_name)
                print(f"Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"Could not add column {col_name}: {e}")
    
    if columns_added:
        conn.commit()
        print(f"\nSuccessfully added {len(columns_added)} columns: {columns_added}")
    else:
        print("\nNo columns needed to be added")
    
    conn.close()

def recreate_social_tables():
    """Drop and recreate all social tables (use with caution - loses data)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables_to_drop = [
        'social_posts', 'social_post_stats', 'social_comments', 
        'social_likes', 'social_follows', 'social_stories',
        'social_story_views', 'social_reports', 'social_saves',
        'social_hashtags', 'social_feed_cache', 'spam_detection_logs'
    ]
    
    for table in tables_to_drop:
        try:
            cursor.execute(f'DROP TABLE IF EXISTS {table}')
            print(f"Dropped table: {table}")
        except sqlite3.OperationalError as e:
            print(f"Could not drop {table}: {e}")
    
    conn.commit()
    conn.close()
    print("\nTables dropped. Restart the backend to recreate them.")

if __name__ == '__main__':
    import sys
    
    print("CONFIT Database Schema Fix")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--recreate':
        print("WARNING: This will delete all social feed data!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            recreate_social_tables()
    else:
        print("Adding missing columns to social_posts...")
        fix_social_posts_table()
        print("\nDone. Restart the backend server.")
