# RFID Attendance Management System

A school attendance system using **FastAPI + SQLite** (server) and **ESP8266 + RC522** (hardware).

---

## Project Structure

```
rfid_attendance/
├── main.py               # FastAPI app — all routes & WebSocket
├── database.py           # SQLAlchemy engine & session
├── models.py             # ORM models (Student, Attendance)
├── schemas.py            # Pydantic request/response schemas
├── crud.py               # Database operations
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html         # Navbar + layout
│   ├── dashboard.html    # Stats + live feed
│   ├── students.html     # CRUD student management
│   └── attendance.html   # History + live feed + CSV export
├── static/
│   ├── css/custom.css
│   └── js/app.js         # WebSocket client + toast + helpers
└── arduino/
    └── rfid_attendance.ino
```

---

## Setup Guide

### 1 — Install Python dependencies

```bash
cd rfid_attendance
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 2 — Start the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server starts and automatically creates `attendance.db` (SQLite) on first run.

Open your browser at **http://localhost:8000**

---

## Deployment on Another PC

1. Copy the entire `rfid_attendance/` folder to the target machine.
2. Make sure Python 3.10+ is installed.
3. Follow the same setup steps above.
4. Find the machine's local IP address:
   - Windows: `ipconfig`
   - macOS/Linux: `ip addr` or `ifconfig`
5. Start the server with `--host 0.0.0.0` so it accepts connections from the ESP8266.
6. Update `SERVER_URL` in the Arduino sketch to `http://<PC-IP>:8000/mark-attendance`.

---

## API Documentation

Full interactive docs available at **http://localhost:8000/docs**

### Students

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/students` | Add new student |
| `GET` | `/students` | List all students |
| `PUT` | `/students/{id}` | Update student |
| `DELETE` | `/students/{id}` | Delete student + records |

**POST /students body:**
```json
{
  "name": "Alan Turing",
  "class_name": "10-A",
  "roll_number": "2024001",
  "rfid_uid": "A1B2C3D4"
}
```

### Attendance

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/mark-attendance` | Scan RFID → mark IN/OUT |
| `GET` | `/attendance/today` | Today's records |
| `GET` | `/attendance/live` | Last 20 records |
| `GET` | `/attendance/history?date=YYYY-MM-DD` | Records for a date |
| `GET` | `/attendance/export?date=YYYY-MM-DD` | Download CSV |

**POST /mark-attendance body:**
```json
{ "rfid_uid": "A1B2C3D4" }
```

**Success response (HTTP 200):**
```json
{ "success": true, "student_name": "Alan Turing", "attendance_type": "IN" }
```

**Invalid RFID response (HTTP 404):**
```json
{ "success": false, "message": "Invalid RFID" }
```

**Duplicate scan response (HTTP 429):**
```json
{ "success": false, "message": "Duplicate scan — please wait a moment" }
```

### WebSocket

Connect to `ws://<host>:8000/ws/attendance` to receive live attendance events as JSON:

```json
{
  "student_name": "Alan Turing",
  "class_name": "10-A",
  "roll_number": "2024001",
  "attendance_type": "IN",
  "timestamp": "2024-09-01 08:32:11"
}
```

---

## Attendance Logic

- **First scan of the day** → `IN`
- **Second scan** → `OUT`
- Alternates automatically per student per day
- Duplicate scans within **10 seconds** are rejected (HTTP 429 → red LED)

---

## Arduino Setup

### Required Libraries (Arduino Library Manager)

- `MFRC522` by GithubCommunity
- `ArduinoJson` by Benoit Blanchon (v6.x)
- ESP8266 board package (URL: `https://arduino.esp8266.com/stable/package_esp8266com_index.json`)

### Wiring

| RC522 Pin | NodeMCU Pin |
|-----------|-------------|
| SDA       | D8          |
| SCK       | D5          |
| MOSI      | D7          |
| MISO      | D6          |
| RST       | D3          |
| 3.3V      | 3V3         |
| GND       | GND         |

| LED | NodeMCU | Resistor |
|-----|---------|----------|
| Green (+) | D1 | 220Ω → GND |
| Red (+)   | D2 | 220Ω → GND |

### LED Signals

| Event | Green LED | Red LED |
|-------|-----------|---------|
| WiFi connecting | — | Blink |
| Ready | 3 flashes | — |
| Marked IN | 2 flashes | — |
| Marked OUT | 1 flash | — |
| Invalid RFID | — | 3 flashes |
| Duplicate scan | — | 1 long flash |
| Server error | — | 2 flashes |

### Configuration

Edit these two lines in `rfid_attendance.ino`:

```cpp
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL    = "http://192.168.1.100:8000/mark-attendance";
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `uvicorn: command not found` | Activate venv: `source venv/bin/activate` |
| Database not created | Ensure you run `uvicorn` from inside `rfid_attendance/` |
| ESP8266 won't connect to WiFi | Double-check SSID/password; use 2.4 GHz only |
| ESP8266 can't reach server | Ensure `--host 0.0.0.0`, check firewall, use PC's LAN IP |
| RFID not reading | Check SPI wiring; RC522 runs on 3.3V (not 5V) |
| "Invalid RFID" on valid card | Register the card's UID in Students → Edit → RFID UID |
| WebSocket shows "Reconnecting" | Server restarted; page auto-reconnects within 3 s |
| Port 8000 in use | Use `--port 8001` (update SERVER_URL in Arduino too) |
