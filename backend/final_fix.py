import sqlite3
import os
import sys

# Force output to file
log_file = open('fix_output.txt', 'w')
sys.stdout = log_file

print("Starting database fix...")

# Drop problematic tables
conn = sqlite3.connect('confit.db')
conn.execute('DROP TABLE IF EXISTS social_posts')
conn.execute('DROP TABLE IF EXISTS social_votes')
conn.commit()
print("Dropped social_posts and social_votes")

# Reinitialize
from database.session import init_db
init_db()
print("Called init_db()")

# Verify
c = conn.cursor()
c.execute('PRAGMA table_info(social_posts)')
cols = [r[1] for r in c.fetchall()]
print(f"social_posts columns: {cols}")
print(f"Has user_id: {'user_id' in cols}")

c.execute('PRAGMA table_info(social_votes)')
cols = [r[1] for r in c.fetchall()]
print(f"social_votes columns: {cols}")

conn.close()
print("Done!")

log_file.close()
