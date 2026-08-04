import os, sqlite3, json, urllib.request
print('CWD:', os.getcwd())
db='stress_data.db'
print('DB exists:', os.path.exists(db))
if os.path.exists(db):
    conn=sqlite3.connect(db)
    conn.row_factory=sqlite3.Row
    cur=conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sensor_log'")
    t=cur.fetchone()
    print('sensor_log exists:', bool(t))
    rows=cur.execute("SELECT id,timestamp,heart_rate,spo2,stress_level FROM sensor_log ORDER BY id DESC LIMIT 5").fetchall()
    print('recent rows count:', len(rows))
    for r in rows:
        print(dict(r))
    conn.close()
else:
    print('No DB file')

for url in ['http://127.0.0.1:8765/health','http://127.0.0.1:8765/latest','http://127.0.0.1:8765/api/history?limit=3','http://127.0.0.1:8765/dashboard?lang=ko']:
    try:
        print('\nGET',url)
        r=urllib.request.urlopen(url, timeout=5)
        data=r.read(1200).decode('utf-8',errors='replace')
        print(data)
    except Exception as e:
        print('ERR',e)
