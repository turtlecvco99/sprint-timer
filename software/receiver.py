from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB = '../data/sprint_data.db'

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS runs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT,
        athlete     TEXT,
        split_0_10  REAL,
        split_10_30 REAL,
        split_30_60 REAL,
        total       REAL,
        top_speed   REAL
    )''')
    conn.commit()
    conn.close()

@app.route('/log', methods=['POST'])
def log_run():
    d = request.json
    conn = sqlite3.connect(DB)
    conn.execute('''INSERT INTO runs
        (date, athlete, split_0_10, split_10_30, split_30_60, total, top_speed)
        VALUES (?,?,?,?,?,?,?)''',
        (datetime.now().isoformat(),
         d.get('athlete', 'Franklin'),
         d['split_0_10'], d['split_10_30'],
         d['split_30_60'], d['total'], d['top_speed']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/status')
def status():
    return jsonify({'status': 'receiver running'})

if __name__ == '__main__':
    init_db()
    print("Receiver live on port 8502")
    app.run(host='0.0.0.0', port=8502)
