import sqlite3

conn = sqlite3.connect('confit.db')
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [row[0] for row in cursor])

cursor = conn.execute('PRAGMA table_info(social_posts)')
print("\nsocial_posts columns:")
for row in cursor:
    print(row)
conn.close()
