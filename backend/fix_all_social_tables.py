"""Complete database fix for CONFIT backend."""
import sqlite3
import os

DB_PATH = r'e:\CONFIT\backend\confit.db'
LOG_PATH = r'e:\CONFIT\backend\fix_log.txt'

def main():
    log_lines = []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    log_lines.append(f"Tables: {tables}")
    
    # Fix social_posts
    cursor.execute("DROP TABLE IF EXISTS social_posts")
    cursor.execute("""
        CREATE TABLE social_posts (
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_user_id ON social_posts(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_visibility ON social_posts(visibility)")
    log_lines.append("Fixed social_posts table")
    
    # Fix social_post_stats
    cursor.execute("DROP TABLE IF EXISTS social_post_stats")
    cursor.execute("""
        CREATE TABLE social_post_stats (
            id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL UNIQUE,
            like_count INTEGER NOT NULL DEFAULT 0,
            comment_count INTEGER NOT NULL DEFAULT 0,
            share_count INTEGER NOT NULL DEFAULT 0,
            save_count INTEGER NOT NULL DEFAULT 0,
            view_count INTEGER NOT NULL DEFAULT 0,
            engagement_rate REAL NOT NULL DEFAULT 0.0,
            trending_score REAL NOT NULL DEFAULT 0.0,
            last_activity_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    log_lines.append("Fixed social_post_stats table")
    
    # Fix social_comments
    cursor.execute("DROP TABLE IF EXISTS social_comments")
    cursor.execute("""
        CREATE TABLE social_comments (
            id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            parent_id TEXT,
            content TEXT NOT NULL,
            mentions TEXT DEFAULT '[]',
            is_edited INTEGER NOT NULL DEFAULT 0,
            is_hidden INTEGER NOT NULL DEFAULT 0,
            like_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_comments_post_id ON social_comments(post_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_comments_user_id ON social_comments(user_id)")
    log_lines.append("Fixed social_comments table")
    
    # Fix social_likes
    cursor.execute("DROP TABLE IF EXISTS social_likes")
    cursor.execute("""
        CREATE TABLE social_likes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, entity_type, entity_id)
        )
    """)
    log_lines.append("Fixed social_likes table")
    
    # Fix social_follows
    cursor.execute("DROP TABLE IF EXISTS social_follows")
    cursor.execute("""
        CREATE TABLE social_follows (
            id TEXT PRIMARY KEY,
            follower_id TEXT NOT NULL,
            following_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(follower_id, following_id)
        )
    """)
    log_lines.append("Fixed social_follows table")
    
    # Fix social_stories
    cursor.execute("DROP TABLE IF EXISTS social_stories")
    cursor.execute("""
        CREATE TABLE social_stories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            outfit_id TEXT,
            media_url TEXT NOT NULL,
            media_type TEXT NOT NULL DEFAULT 'image',
            caption TEXT,
            hashtags TEXT DEFAULT '[]',
            duration_secs INTEGER,
            view_count INTEGER NOT NULL DEFAULT 0,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    log_lines.append("Fixed social_stories table")
    
    # Fix social_story_views
    cursor.execute("DROP TABLE IF EXISTS social_story_views")
    cursor.execute("""
        CREATE TABLE social_story_views (
            id TEXT PRIMARY KEY,
            story_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(story_id, user_id)
        )
    """)
    log_lines.append("Fixed social_story_views table")
    
    # Fix social_reports
    cursor.execute("DROP TABLE IF EXISTS social_reports")
    cursor.execute("""
        CREATE TABLE social_reports (
            id TEXT PRIMARY KEY,
            reporter_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            reviewed_by TEXT,
            reviewed_at TEXT,
            action_taken TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    log_lines.append("Fixed social_reports table")
    
    # Fix social_saves
    cursor.execute("DROP TABLE IF EXISTS social_saves")
    cursor.execute("""
        CREATE TABLE social_saves (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            post_id TEXT NOT NULL,
            collection_name TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, post_id)
        )
    """)
    log_lines.append("Fixed social_saves table")
    
    # Fix social_hashtags
    cursor.execute("DROP TABLE IF EXISTS social_hashtags")
    cursor.execute("""
        CREATE TABLE social_hashtags (
            id TEXT PRIMARY KEY,
            tag TEXT NOT NULL UNIQUE,
            post_count INTEGER NOT NULL DEFAULT 0,
            trending_score REAL NOT NULL DEFAULT 0.0,
            is_trending INTEGER NOT NULL DEFAULT 0,
            last_used_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    log_lines.append("Fixed social_hashtags table")
    
    # Fix social_feed_cache
    cursor.execute("DROP TABLE IF EXISTS social_feed_cache")
    cursor.execute("""
        CREATE TABLE social_feed_cache (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            post_id TEXT NOT NULL,
            feed_type TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            score REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            UNIQUE(user_id, post_id, feed_type)
        )
    """)
    log_lines.append("Fixed social_feed_cache table")
    
    # Fix spam_detection_logs
    cursor.execute("DROP TABLE IF EXISTS spam_detection_logs")
    cursor.execute("""
        CREATE TABLE spam_detection_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            action_type TEXT NOT NULL,
            content_hash TEXT,
            is_spam INTEGER NOT NULL DEFAULT 0,
            confidence REAL NOT NULL DEFAULT 0.0,
            detection_method TEXT,
            extra_data TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    log_lines.append("Fixed spam_detection_logs table")
    
    # Fix social_votes
    cursor.execute("DROP TABLE IF EXISTS social_votes")
    cursor.execute("""
        CREATE TABLE social_votes (
            id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            voter_user_id TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_votes_post_id ON social_votes(post_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_votes_voter_user_id ON social_votes(voter_user_id)")
    log_lines.append("Fixed social_votes table")
    
    conn.commit()
    conn.close()
    
    log_lines.append("\n=== ALL TABLES FIXED ===")
    log_lines.append("Restart the backend server now!")
    
    # Write log
    with open(LOG_PATH, 'w') as f:
        f.write('\n'.join(log_lines))
    
    print("Done! Check fix_log.txt for details.")

if __name__ == '__main__':
    main()
