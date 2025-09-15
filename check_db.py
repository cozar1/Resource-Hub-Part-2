import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Check table schema
cursor.execute('PRAGMA table_info(asset)')
print('Asset table schema:')
for row in cursor.fetchall():
    print(row)

print('\nSample asset data:')
cursor.execute('SELECT * FROM asset LIMIT 1')
asset_data = cursor.fetchone()
if asset_data:
    print(f"Asset data: {asset_data}")
    print(f"Length: {len(asset_data)}")
    for i, field in enumerate(asset_data):
        print(f"Index {i}: {field}")

conn.close()
