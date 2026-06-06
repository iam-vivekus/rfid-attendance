import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    class_name = Column(String(50), nullable=False)
    roll_number = Column(String(20), unique=True, nullable=False)
    rfid_uid = Column(String(50), unique=True, nullable=True)

    attendances = relationship(
        "Attendance", back_populates="student", cascade="all, delete-orphan"
    )


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    attendance_type = Column(String(3), nullable=False)  # IN or OUT

    student = relationship("Student", back_populates="attendances")
