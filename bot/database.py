import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('user_progress.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_seen TIMESTAMP,
                  last_activity TIMESTAMP,
                  topics_completed TEXT)''')
    conn.commit()
    conn.close()

def get_user_progress(user_id):
    conn = sqlite3.connect('user_progress.db')
    c = conn.cursor()
    c.execute("SELECT topics_completed FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return [int(x) for x in row[0].split(',') if x]
    return []

def update_user_progress(user_id, completed_topics, username=None):
    topics_str = ','.join(map(str, completed_topics))
    now = datetime.now()
    conn = sqlite3.connect('user_progress.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if c.fetchone():
        c.execute('''UPDATE users 
                     SET last_activity=?, topics_completed=?
                     WHERE user_id=?''',
                  (now, topics_str, user_id))
    else:
        c.execute('''INSERT INTO users 
                     (user_id, username, first_seen, last_activity, topics_completed)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, username, now, now, topics_str))
    conn.commit()
    conn.close()

def calculate_percent(completed, total):
    return int((len(completed) / total) * 100) if total else 0