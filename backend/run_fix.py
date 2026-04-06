"""Fix social_posts and social_votes tables."""
import sqlite3
import os

# Change to backend directory
os.chdir(r'e:\CONFIT\backend')

conn = sqlite3.connect('confit.db')
c = conn.cursor()

# Fix social_posts
c.execute('DROP TABLE IF EXISTS social_posts')
c.execute('''CREATE TABLE social_posts (
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
)''')
c.execute('CREATE INDEX idx_social_posts_user_id ON social_posts(user_id)')
c.execute('CREATE INDEX idx_social_posts_visibility ON social_posts(visibility)')

# Fix social_votes
c.execute('DROP TABLE IF EXISTS social_votes')
c.execute('''CREATE TABLE social_votes (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    voter_user_id TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)''')
c.execute('CREATE INDEX idx_social_votes_post_id ON social_votes(post_id)')
c.execute('CREATE INDEX idx_social_votes_voter_user_id ON social_votes(voter_user_id)')

conn.commit()

# Verify
with open('db_fix_result.txt', 'w') as f:
    c.execute('PRAGMA table_info(social_posts)')
    cols = c.fetchall()
    f.write('social_posts columns: ' + str([col[1] for col in cols]) + '\n')
    
    c.execute('PRAGMA table_info(social_votes)')
    cols = c.fetchall()
    f.write('social_votes columns: ' + str([col[1] for col in cols]) + '\n')
    
    f.write('\nDatabase fixed successfully!\n')

conn.close()
print('Done!')
