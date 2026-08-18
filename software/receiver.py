from flask import Flask, request, jsonify
import sqlite3
import os
import re
import socket
import threading
import time
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False

app = Flask(__name__)
_here = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(_here, '..', 'data', 'sprint_data.db')

# Gate nodes talk to this receiver over UDP, not HTTP — light beam breaks
# need to fire the instant they happen, no HTTP handshake overhead.
UDP_PORT = 8503
GATE_TIMEOUT_S = 15  # abandon a run if a gate never reports back (missed beam break, dead WiFi, etc.)

# The hub (4 gates wired into one board) reports over USB serial instead —
# it prints its own "Gate N: X.XX ms" summary once a run finishes, so no
# aggregation is needed here, just parsing.
SERIAL_PORT = os.environ.get('DRIVE_PHASE_SERIAL_PORT', '')
SERIAL_BAUD = int(os.environ.get('DRIVE_PHASE_SERIAL_BAUD', '9600'))
_GATE_LINE_RE = re.compile(r'Gate\s+(\d+)\s*:\s*([\d.]+)\s*ms', re.IGNORECASE)

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


def _pick_serial_port():
    if SERIAL_PORT:
        return SERIAL_PORT
    ports = list(serial.tools.list_ports.comports())
    if len(ports) == 1:
        print(f"[hub] auto-detected serial port: {ports[0].device}")
        return ports[0].device
    if not ports:
        print("[hub] no serial ports found — plug in the hub, or set DRIVE_PHASE_SERIAL_PORT")
    else:
        names = ', '.join(p.device for p in ports)
        print(f"[hub] multiple serial ports found ({names}) — set DRIVE_PHASE_SERIAL_PORT to pick one")
    return None


def _serial_listener():
    """Background thread: reads the hub's plain-text run summaries over USB
    serial and logs a completed run each time all 4 gate times arrive.

    Expected lines (anywhere in the stream, other lines are ignored):
      "Gate 0: 0.00 ms"
      "Gate 1: <cumulative ms since gate 0>"
      "Gate 2: <cumulative ms since gate 0>"
      "Gate 3: <cumulative ms since gate 0>"
    """
    gate_ms = {}
    while True:
        port = _pick_serial_port()
        if not port:
            time.sleep(5)
            continue
        try:
            with serial.Serial(port, SERIAL_BAUD, timeout=2) as ser:
                print(f"[hub] connected on {port} @ {SERIAL_BAUD} baud")
                gate_ms.clear()
                while True:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                    m = _GATE_LINE_RE.search(line)
                    if not m:
                        continue
                    gate_id, ms = int(m.group(1)), float(m.group(2))
                    gate_ms[gate_id] = ms
                    if all(g in gate_ms for g in (0, 1, 2, 3)):
                        base = gate_ms[0]
                        elapsed_10 = (gate_ms[1] - base) / 1000.0
                        elapsed_30 = (gate_ms[2] - base) / 1000.0
                        elapsed_60 = (gate_ms[3] - base) / 1000.0
                        gate_ms.clear()
                        _complete_run(elapsed_10, elapsed_30, elapsed_60)
        except (serial.SerialException, OSError) as e:
            print(f"[hub] serial connection lost ({e}) — retrying in 5s")
            time.sleep(5)


if __name__ == '__main__':
    init_db()
    threading.Thread(target=_gate_listener, daemon=True).start()
    if _SERIAL_AVAILABLE:
        threading.Thread(target=_serial_listener, daemon=True).start()
    else:
        print("[hub] pyserial not installed — skipping USB hub listener (pip install pyserial)")
    print("Receiver live on port 8502 (HTTP), 8503 (UDP gate feed), and USB serial (hub)")
    app.run(host='0.0.0.0', port=8502)
