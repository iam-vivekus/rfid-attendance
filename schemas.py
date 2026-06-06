from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StudentCreate(BaseModel):
    name: str
    class_name: str
    roll_number: str
    rfid_uid: Optional[str] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    class_name: Optional[str] = None
    roll_number: Optional[str] = None
    rfid_uid: Optional[str] = None


class StudentResponse(BaseModel):
    id: int
    name: str
    class_name: str
    roll_number: str
    rfid_uid: Optional[str] = None

    model_config = {"from_attributes": True}


class AttendanceRecord(BaseModel):
    id: int
    student_id: int
    student_name: str
    class_name: str
    roll_number: str
    timestamp: str
    attendance_type: str


class RFIDRequest(BaseModel):
    rfid_uid: str


class AttendanceMarkResponse(BaseModel):
    success: bool
    student_name: Optional[str] = None
    attendance_type: Optional[str] = None
    message: Optional[str] = None
