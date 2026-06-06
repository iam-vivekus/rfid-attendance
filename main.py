import csv
import datetime
import io
import json
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import crud
import models
import schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Attendance System", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ── Page routes ───────────────────────────────────────────────────────────────

@app.get("/")
async def page_dashboard(request: Request, db: Session = Depends(get_db)):
    students = crud.get_students(db)
    today_records = crud.get_today_attendance(db)
    present = crud.get_today_present_count(db)
    return templates.TemplateResponse(request, "dashboard.html", {
        "total_students": len(students),
        "present_today": present,
        "scan_count": len(today_records),
        "date": datetime.date.today().strftime("%B %d, %Y"),
        "recent": crud.serialize_records(today_records[:10]),
    })


@app.get("/students-page")
async def page_students(request: Request, db: Session = Depends(get_db)):
    students = crud.get_students(db)
    return templates.TemplateResponse(request, "students.html", {
        "students": students,
    })


@app.get("/attendance-page")
async def page_attendance(request: Request):
    return templates.TemplateResponse(request, "attendance.html")


# ── Student API ───────────────────────────────────────────────────────────────

@app.post("/students", response_model=schemas.StudentResponse, status_code=201)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    if crud.get_student_by_roll(db, student.roll_number):
        raise HTTPException(status_code=400, detail="Roll number already registered")
    if student.rfid_uid and crud.get_student_by_rfid(db, student.rfid_uid):
        raise HTTPException(status_code=400, detail="RFID UID already mapped to another student")
    return crud.create_student(db, student)


@app.get("/students", response_model=List[schemas.StudentResponse])
def list_students(db: Session = Depends(get_db)):
    return crud.get_students(db)


@app.put("/students/{student_id}", response_model=schemas.StudentResponse)
def update_student(
    student_id: int, student: schemas.StudentUpdate, db: Session = Depends(get_db)
):
    db_student = crud.get_student(db, student_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.rfid_uid:
        existing = crud.get_student_by_rfid(db, student.rfid_uid)
        if existing and existing.id != student_id:
            raise HTTPException(status_code=400, detail="RFID UID already mapped to another student")
    return crud.update_student(db, student_id, student)


@app.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    if not crud.get_student(db, student_id):
        raise HTTPException(status_code=404, detail="Student not found")
    crud.delete_student(db, student_id)
    return {"success": True, "message": "Student deleted"}


# ── Attendance API ────────────────────────────────────────────────────────────

@app.post("/mark-attendance")
async def mark_attendance(payload: schemas.RFIDRequest, db: Session = Depends(get_db)):
    student = crud.get_student_by_rfid(db, payload.rfid_uid)
    if not student:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Invalid RFID"},
        )

    # Duplicate-scan guard: reject if last scan was within 10 seconds
    last = crud.get_last_attendance(db, student.id)
    if last:
        elapsed = (datetime.datetime.now() - last.timestamp).total_seconds()
        if elapsed < 10:
            return JSONResponse(
                status_code=429,
                content={"success": False, "message": "Duplicate scan — please wait a moment"},
            )

    attendance_type = crud.determine_attendance_type(db, student.id)
    record = crud.create_attendance(db, student.id, attendance_type)

    broadcast_payload = {
        "student_name": student.name,
        "class_name": student.class_name,
        "roll_number": student.roll_number,
        "attendance_type": attendance_type,
        "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    }
    await manager.broadcast(broadcast_payload)

    return {
        "success": True,
        "student_name": student.name,
        "attendance_type": attendance_type,
    }


@app.get("/attendance/today")
def attendance_today(db: Session = Depends(get_db)):
    records = crud.get_today_attendance(db)
    return crud.serialize_records(records)


@app.get("/attendance/live")
def attendance_live(db: Session = Depends(get_db)):
    records = crud.get_recent_attendance(db, limit=20)
    return crud.serialize_records(records)


@app.get("/attendance/history")
def attendance_history(date: str = None, db: Session = Depends(get_db)):
    if date:
        try:
            target = datetime.date.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date — use YYYY-MM-DD")
    else:
        target = datetime.date.today()
    records = crud.get_attendance_by_date(db, target)
    return crud.serialize_records(records)


@app.get("/attendance/export")
def attendance_export(date: str = None, db: Session = Depends(get_db)):
    if date:
        try:
            target = datetime.date.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date — use YYYY-MM-DD")
    else:
        target = datetime.date.today()

    records = crud.get_attendance_by_date(db, target)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["#", "Student Name", "Class", "Roll Number", "Date", "Time", "Type"])
    for i, r in enumerate(records, 1):
        writer.writerow([
            i,
            r.student.name,
            r.student.class_name,
            r.student.roll_number,
            r.timestamp.strftime("%Y-%m-%d"),
            r.timestamp.strftime("%H:%M:%S"),
            r.attendance_type,
        ])

    output.seek(0)
    filename = f"attendance_{target}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/attendance")
async def ws_attendance(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
