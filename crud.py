import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
import models
import schemas


# ── Students ──────────────────────────────────────────────────────────────────

def get_student(db: Session, student_id: int):
    return db.query(models.Student).filter(models.Student.id == student_id).first()


def get_student_by_roll(db: Session, roll_number: str):
    return db.query(models.Student).filter(models.Student.roll_number == roll_number).first()


def get_student_by_rfid(db: Session, rfid_uid: str):
    return db.query(models.Student).filter(models.Student.rfid_uid == rfid_uid).first()


def get_students(db: Session):
    return db.query(models.Student).order_by(models.Student.name).all()


def create_student(db: Session, student: schemas.StudentCreate):
    db_student = models.Student(**student.model_dump())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


def update_student(db: Session, student_id: int, student: schemas.StudentUpdate):
    db_student = get_student(db, student_id)
    for key, value in student.model_dump(exclude_unset=True).items():
        setattr(db_student, key, value)
    db.commit()
    db.refresh(db_student)
    return db_student


def delete_student(db: Session, student_id: int):
    db_student = get_student(db, student_id)
    db.delete(db_student)
    db.commit()


# ── Attendance ────────────────────────────────────────────────────────────────

def get_last_attendance(db: Session, student_id: int):
    return (
        db.query(models.Attendance)
        .filter(models.Attendance.student_id == student_id)
        .order_by(models.Attendance.timestamp.desc())
        .first()
    )


def determine_attendance_type(db: Session, student_id: int) -> str:
    today = datetime.date.today()
    last = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.student_id == student_id,
            func.date(models.Attendance.timestamp) == today,
        )
        .order_by(models.Attendance.timestamp.desc())
        .first()
    )
    if last is None or last.attendance_type == "OUT":
        return "IN"
    return "OUT"


def create_attendance(db: Session, student_id: int, attendance_type: str):
    record = models.Attendance(
        student_id=student_id,
        attendance_type=attendance_type,
        timestamp=datetime.datetime.now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_today_attendance(db: Session):
    today = datetime.date.today()
    return (
        db.query(models.Attendance)
        .filter(func.date(models.Attendance.timestamp) == today)
        .order_by(models.Attendance.timestamp.desc())
        .all()
    )


def get_attendance_by_date(db: Session, date: datetime.date):
    return (
        db.query(models.Attendance)
        .filter(func.date(models.Attendance.timestamp) == date)
        .order_by(models.Attendance.timestamp)
        .all()
    )


def get_recent_attendance(db: Session, limit: int = 20):
    return (
        db.query(models.Attendance)
        .order_by(models.Attendance.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_today_present_count(db: Session) -> int:
    today = datetime.date.today()
    result = (
        db.query(func.count(func.distinct(models.Attendance.student_id)))
        .filter(func.date(models.Attendance.timestamp) == today)
        .scalar()
    )
    return result or 0


def _serialize(record) -> dict:
    return {
        "id": record.id,
        "student_id": record.student_id,
        "student_name": record.student.name,
        "class_name": record.student.class_name,
        "roll_number": record.student.roll_number,
        "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "attendance_type": record.attendance_type,
    }


def serialize_records(records) -> list:
    return [_serialize(r) for r in records]
