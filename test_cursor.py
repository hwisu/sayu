import sqlite3
import json

db_path = "/Users/hwisookim/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get some bubble entries
cursor.execute("SELECT key, substr(value, 1, 200) FROM cursorDiskKV WHERE key LIKE 'bubbleId:%' LIMIT 5")
results = cursor.fetchall()

print(f"Found {len(results)} bubble entries")
for key, value in results:
    try:
        data = json.loads(value[:200] + "}")  # Try partial parse
        msg_type = data.get('type', 'unknown')
        has_text = 'text' in data
        print(f"Key: {key[:50]}... Type: {msg_type}, Has text: {has_text}")
    except:
        print(f"Key: {key[:50]}... (couldn't parse)")

conn.close()
