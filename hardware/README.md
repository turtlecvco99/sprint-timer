# Sprint timing gates — hardware setup

Four IR break-beam gates (0m / 10m / 30m / 60m), each on its own ESP32,
report times over WiFi to `software/receiver.py`, which computes splits
and writes them straight into the same database the dashboard reads.
Nothing here needs the dashboard app running — the receiver and the
Streamlit app are two independent processes that just happen to share
one database file.

## What you need

- 4x ESP32 dev boards (any common one — DevKitC, NodeMCU-32S, etc.)
- 4x IR break-beam sensor modules (cheap "IR obstacle avoidance" modules
  with an OUT/DO pin work fine — they don't need to be a matched
  emitter/receiver pair, just something that flips a digital pin when a
  runner passes through)
- A laptop (or any always-on machine) on the same WiFi network to run
  `receiver.py` — this is what the dashboard's database lives next to
- Power for each gate (USB battery banks work well for field use)

## 1. Wire each gate

Sensor `OUT`/`DO` pin -> ESP32 `GPIO 4` (configurable in the sketch)
Sensor `VCC` -> `3V3` or `5V` per your module's spec
Sensor `GND` -> `GND`

Most cheap IR break-beam modules pull the output pin **low** when the
beam is broken. If yours reads backwards (triggers when *clear*, not
when *broken*), flip `BEAM_BROKEN_STATE` in the sketch from `LOW` to
`HIGH`.

## 2. Flash the firmware

All four boards run the exact same file: `hardware/gate_node/gate_node.ino`.
Open it in the Arduino IDE (with ESP32 board support installed) and edit
the four values at the top before flashing **each** board:

```cpp
const int GATE_ID = 1;                     // 0=start/0m, 1=10m, 2=30m, 3=60m — different per board
const char* WIFI_SSID     = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const IPAddress RECEIVER_IP(192, 168, 1, 50);   // the laptop running receiver.py — see below
```

`GATE_ID` is the only thing that changes what a board actually does:
- **0** — the start gate. Breaks its beam, broadcasts `START`, that's it.
- **1, 2, 3** — wait for `START`, time their own beam break locally, and
  report the elapsed time back to the receiver.

Also check `BROADCAST_IP` matches your WiFi's subnet (e.g. if your
router hands out `192.168.1.x` addresses, it should be `192.168.1.255`).

## 3. Give the receiver machine a fixed IP

Every gate needs to know the receiver's address ahead of time, so it
shouldn't move. Either set a DHCP reservation for it in your router's
admin page (search "\[router model] DHCP reservation"), or just check
its current address with `ifconfig` (Mac/Linux) or `ipconfig` (Windows)
and use that — just be aware it can change if you don't reserve it.

## 4. Run the receiver

```bash
cd software
python receiver.py
```

This starts two listeners on the same machine:
- HTTP on port **8502** — manual entry (`/log`) and the arm control the
  dashboard uses (`/arm`, `/status`)
- UDP on port **8503** — where the gate nodes actually report in

Leave this running for the whole session. It's independent of the
Streamlit app (`streamlit run software/dashboard.py`) — start both, in
either order, on the same machine.

## 5. Use it

1. Power on all four gates and wait for them to connect to WiFi (check
   each board's Serial Monitor for "Connected, IP: ...").
2. In the dashboard, go to **Settings → Gate Timing** (coach account) —
   it'll show "Gate receiver online" if `receiver.py` is reachable.
3. Pick the athlete about to run and hit **ARM**.
4. Have them run through all four gates. The completed run shows up
   in the dashboard automatically — no manual entry needed.
5. Re-arm before every runner. If the same athlete is doing repeat reps,
   you don't need to re-arm between each one — it stays armed until you
   change it.

## Troubleshooting

- **Nothing logs after a run**: check `receiver.py`'s terminal output —
  it prints `[gates] run started` when gate 0 fires and
  `[gates] logged run for <athlete>: ...` when all three splits arrive.
  If you see "run started" but never "logged", one of gates 1/2/3 isn't
  reaching the receiver — check its WiFi connection and `RECEIVER_IP`.
- **A gate never sees START**: confirm `BROADCAST_IP` matches your
  actual subnet, and that all devices (gates + receiver machine) are on
  the same WiFi network, not a guest network that isolates clients from
  each other.
- **Runs looking way too fast/slow**: almost always a `GATE_ID` mixup —
  double check which physical distance each board is actually flashed
  for.
- **Testing without hardware**: you can simulate a full run by sending
  UDP packets by hand — see the wire format documented at the top of
  `receiver.py`.
