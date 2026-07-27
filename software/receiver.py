from flask import Flask, request, jsonify
import sqlite3
import os
import socket
import threading
import time
from datetime import datetime

app = Flask(__name__)
_here = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(_here, '..', 'data', 'sprint_data.db')

# Gate nodes talk to this receiver over UDP, not HTTP — light beam breaks
# need to fire the instant they happen, no HTTP handshake overhead.
UDP_PORT = 8503
GATE_TIMEOUT_S = 15  # abandon a run if a gate never reports back (missed beam break, dead WiFi, etc.)

_armed_lock = threading.Lock()
_armed_athlete = 'Franklin'

_run_lock = threading.Lock()
_run_open_since = None
_run_splits = {}  # gate_id (1, 2, 3) -> elapsed seconds since the start beam broke


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


def _insert_run(athlete, s1, s2, s3, total, top_speed):
    conn = sqlite3.connect(DB)
    conn.execute('''INSERT INTO runs
        (date, athlete, split_0_10, split_10_30, split_30_60, total, top_speed)
        VALUES (?,?,?,?,?,?,?)''',
        (datetime.now().isoformat(), athlete, s1, s2, s3, total, top_speed))
    conn.commit()
    conn.close()


@app.route('/log', methods=['POST'])
def log_run():
    """Manual / direct entry point — takes a complete, already-split run."""
    d = request.json
    _insert_run(d.get('athlete', 'Franklin'), d['split_0_10'], d['split_10_30'],
                d['split_30_60'], d['total'], d['top_speed'])
    return jsonify({'status': 'ok'})


@app.route('/arm', methods=['GET', 'POST'])
def arm():
    """Tell the receiver which athlete the next completed run from the gates belongs to."""
    global _armed_athlete
    if request.method == 'POST':
        name = (request.json or {}).get('athlete', '').strip()
        if not name:
            return jsonify({'status': 'error', 'message': 'athlete required'}), 400
        with _armed_lock:
            _armed_athlete = name
        return jsonify({'status': 'ok', 'armed_athlete': name})
    with _armed_lock:
        return jsonify({'armed_athlete': _armed_athlete})


@app.route('/status')
def status():
    with _armed_lock:
        armed = _armed_athlete
    return jsonify({'status': 'receiver running', 'armed_athlete': armed})


def _complete_run(elapsed_10, elapsed_30, elapsed_60):
    s1 = elapsed_10
    s2 = elapsed_30 - elapsed_10
    s3 = elapsed_60 - elapsed_30
    total = elapsed_60
    top_speed = round(30 / s3 * 2.237, 2) if s3 > 0 else 0.0
    with _armed_lock:
        athlete = _armed_athlete
    _insert_run(athlete, round(s1, 3), round(s2, 3), round(s3, 3), round(total, 3), top_speed)
    print(f"[gates] logged run for {athlete}: {total:.3f}s "
          f"(splits {s1:.3f}/{s2:.3f}/{s3:.3f})")


def _check_run_timeout():
    global _run_open_since, _run_splits
    with _run_lock:
        if _run_open_since and time.time() - _run_open_since > GATE_TIMEOUT_S:
            print("[gates] run timed out waiting for all splits — discarding")
            _run_splits = {}
            _run_open_since = None


def _gate_listener():
    """Background thread: receives UDP packets from the gate ESP32s and
    assembles them into one completed run.

    Wire format (plain text UDP payloads):
      "START"              — gate 0 (0m) broke its beam, a new run has begun
      "SPLIT:<id>:<secs>"   — gate <id> (1=10m, 2=30m, 3=60m) reports its own
                              elapsed time in seconds since it saw the START
    """
    global _run_open_since, _run_splits
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', UDP_PORT))
    sock.settimeout(1.0)
    print(f"[gates] listening for gate nodes on UDP :{UDP_PORT}")
    while True:
        try:
            data, _addr = sock.recvfrom(256)
        except socket.timeout:
            _check_run_timeout()
            continue

        msg = data.decode('utf-8', errors='ignore').strip()
        if msg == 'START':
            with _run_lock:
                _run_splits = {}
                _run_open_since = time.time()
            print("[gates] run started")
            continue

        if msg.startswith('SPLIT:'):
            try:
                _, gate_id_s, elapsed_s = msg.split(':')
                gate_id, elapsed = int(gate_id_s), float(elapsed_s)
            except ValueError:
                continue
            completed = None
            with _run_lock:
                if _run_open_since is None:
                    continue  # stray split with no run in progress — ignore
                _run_splits[gate_id] = elapsed
                if all(g in _run_splits for g in (1, 2, 3)):
                    completed = (_run_splits[1], _run_splits[2], _run_splits[3])
                    _run_splits = {}
                    _run_open_since = None
            if completed:
                _complete_run(*completed)


if __name__ == '__main__':
    init_db()
    threading.Thread(target=_gate_listener, daemon=True).start()
    print("Receiver live on port 8502 (HTTP) and 8503 (UDP gate feed)")
    app.run(host='0.0.0.0', port=8502)
