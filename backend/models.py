from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    receptionist = "receptionist"
    nurse = "nurse"
    doctor = "doctor"
    coordinator = "coordinator"
    technician = "technician"
    pathologist = "pathologist"

class VisitStatus(str, enum.Enum):
    cancelled = "Cancelled"
    scheduled = "Scheduled"
    checked_in = "Checked In"
    waiting = "Waiting"
    in_consultation = "In Consultation"
    completed = "Completed"

class OrderStatus(str, enum.Enum):
    ordered = "Ordered"
    assigned = "Assigned"
    in_progress = "In Progress"
    completed = "Completed"
    cancelled = "Cancelled"
    partially_completed = "Partially Completed"

class SampleStatus(str, enum.Enum):
    awaiting_collection = "Awaiting Collection"
    collected = "Collected"
    received = "Received"
    accepted = "Accepted"
    processing = "Processing"
    processed = "Processed"
    rejected = "Rejected"
    recollection_requested = "Recollection Requested"

class ResultStatus(str, enum.Enum):
    awaiting_result = "Awaiting Result"
    received = "Received"
    pending_review = "Pending Review"
    approved = "Approved/Released"
    held = "Held"
    rerun_requested = "Rerun Requested"

class Priority(str, enum.Enum):
    routine = "Routine"
    urgent = "Urgent"
    stat = "STAT"

class AbhaStatus(str, enum.Enum):
    not_linked = "Not Linked"
    unverified = "Unverified"
    verified = "Verified"


# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uhid: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    dob: Mapped[Optional[str]] = mapped_column(String(20))
    gender: Mapped[Optional[str]] = mapped_column(String(10))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    address: Mapped[Optional[str]] = mapped_column(Text)
    blood_group: Mapped[Optional[str]] = mapped_column(String(5))
    allergies: Mapped[Optional[str]] = mapped_column(Text)
    abha_number: Mapped[Optional[str]] = mapped_column(String(30))
    abha_status: Mapped[AbhaStatus] = mapped_column(SAEnum(AbhaStatus), default=AbhaStatus.not_linked)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    visits: Mapped[list["OpdVisit"]] = relationship("OpdVisit", back_populates="patient")


class OpdVisit(Base):
    __tablename__ = "opd_visits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visit_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    department: Mapped[Optional[str]] = mapped_column(String(50))
    token_number: Mapped[Optional[str]] = mapped_column(String(20))
    status: Mapped[VisitStatus] = mapped_column(SAEnum(VisitStatus), default=VisitStatus.scheduled)
    appointment_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="visits")
    doctor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[doctor_id])
    vitals: Mapped[Optional["Vitals"]] = relationship("Vitals", back_populates="visit", uselist=False)
    consultation: Mapped[Optional["Consultation"]] = relationship("Consultation", back_populates="visit", uselist=False)
    lab_orders: Mapped[list["LabOrder"]] = relationship("LabOrder", back_populates="visit")


class Vitals(Base):
    __tablename__ = "vitals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("opd_visits.id"), unique=True)
    nurse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    temperature: Mapped[Optional[float]] = mapped_column(Float)
    bp_systolic: Mapped[Optional[int]] = mapped_column(Integer)
    bp_diastolic: Mapped[Optional[int]] = mapped_column(Integer)
    pulse: Mapped[Optional[int]] = mapped_column(Integer)
    spo2: Mapped[Optional[float]] = mapped_column(Float)
    height_cm: Mapped[Optional[float]] = mapped_column(Float)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float)
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    ready_for_doctor: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    visit: Mapped["OpdVisit"] = relationship("OpdVisit", back_populates="vitals")
    nurse: Mapped[Optional["User"]] = relationship("User", foreign_keys=[nurse_id])


class Consultation(Base):
    __tablename__ = "consultations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("opd_visits.id"), unique=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    complaints: Mapped[Optional[str]] = mapped_column(Text)
    examination: Mapped[Optional[str]] = mapped_column(Text)
    diagnosis: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    visit: Mapped["OpdVisit"] = relationship("OpdVisit", back_populates="consultation")
    doctor: Mapped["User"] = relationship("User", foreign_keys=[doctor_id])
    prescriptions: Mapped[list["Prescription"]] = relationship("Prescription", back_populates="consultation")


class Prescription(Base):
    __tablename__ = "prescriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    consultation_id: Mapped[int] = mapped_column(ForeignKey("consultations.id"))
    medicine: Mapped[str] = mapped_column(String(100))
    dosage: Mapped[Optional[str]] = mapped_column(String(100))
    frequency: Mapped[Optional[str]] = mapped_column(String(100))
    duration: Mapped[Optional[str]] = mapped_column(String(100))
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    advice: Mapped[Optional[str]] = mapped_column(Text)

    consultation: Mapped["Consultation"] = relationship("Consultation", back_populates="prescriptions")


class MedicalHistory(Base):
    __tablename__ = "medical_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    condition: Mapped[Optional[str]] = mapped_column(String(200))
    current_medicines: Mapped[Optional[str]] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LabTestCatalogue(Base):
    __tablename__ = "lab_test_catalogue"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[Optional[str]] = mapped_column(String(50))
    sample_type: Mapped[Optional[str]] = mapped_column(String(50))
    turnaround_minutes: Mapped[int] = mapped_column(Integer, default=60)


class LabOrder(Base):
    __tablename__ = "lab_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("opd_visits.id"))
    ordered_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    priority: Mapped[Priority] = mapped_column(SAEnum(Priority), default=Priority.routine)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.ordered)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    visit: Mapped["OpdVisit"] = relationship("OpdVisit", back_populates="lab_orders")
    ordered_by_user: Mapped["User"] = relationship("User", foreign_keys=[ordered_by])
    order_tests: Mapped[list["LabOrderTest"]] = relationship("LabOrderTest", back_populates="order")
    technician_assignment: Mapped[Optional["TechnicianAssignment"]] = relationship("TechnicianAssignment", back_populates="order", uselist=False)


class LabOrderTest(Base):
    __tablename__ = "lab_order_tests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("lab_orders.id"))
    test_id: Mapped[int] = mapped_column(ForeignKey("lab_test_catalogue.id"))

    order: Mapped["LabOrder"] = relationship("LabOrder", back_populates="order_tests")
    test: Mapped["LabTestCatalogue"] = relationship("LabTestCatalogue")


class TechnicianAssignment(Base):
    __tablename__ = "technician_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("lab_orders.id"), unique=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order: Mapped["LabOrder"] = relationship("LabOrder", back_populates="technician_assignment")
    technician: Mapped["User"] = relationship("User", foreign_keys=[technician_id])
    assigned_by_user: Mapped["User"] = relationship("User", foreign_keys=[assigned_by])


class Sample(Base):
    __tablename__ = "samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sample_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("lab_orders.id"))
    collected_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    status: Mapped[SampleStatus] = mapped_column(SAEnum(SampleStatus), default=SampleStatus.awaiting_collection)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    barcode: Mapped[Optional[str]] = mapped_column(String(50))
    collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order: Mapped["LabOrder"] = relationship("LabOrder")
    collected_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[collected_by])
    lab_results: Mapped[list["LabResult"]] = relationship("LabResult", back_populates="sample")


class LabResult(Base):
    __tablename__ = "lab_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sample_id: Mapped[int] = mapped_column(ForeignKey("samples.id"))
    test_id: Mapped[int] = mapped_column(ForeignKey("lab_test_catalogue.id"))
    run_number: Mapped[int] = mapped_column(Integer, default=1)
    value: Mapped[Optional[str]] = mapped_column(Text)
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    ref_range: Mapped[Optional[str]] = mapped_column(String(50))
    flag: Mapped[Optional[str]] = mapped_column(String(20))  # H, L, HH, LL, Critical
    qc_status: Mapped[Optional[str]] = mapped_column(String(20))
    analyser_flags: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[ResultStatus] = mapped_column(SAEnum(ResultStatus), default=ResultStatus.awaiting_result)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sample: Mapped["Sample"] = relationship("Sample", back_populates="lab_results")
    test: Mapped["LabTestCatalogue"] = relationship("LabTestCatalogue")
    review_assignment: Mapped[Optional["ReviewAssignment"]] = relationship("ReviewAssignment", back_populates="result", uselist=False)


class ReviewAssignment(Base):
    __tablename__ = "review_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("lab_results.id"), unique=True)
    pathologist_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    decision: Mapped[Optional[str]] = mapped_column(String(30))  # approved, held, rerun
    hold_reason: Mapped[Optional[str]] = mapped_column(Text)
    notification_recorded: Mapped[bool] = mapped_column(Boolean, default=False)

    result: Mapped["LabResult"] = relationship("LabResult", back_populates="review_assignment")
    pathologist: Mapped["User"] = relationship("User", foreign_keys=[pathologist_id])
    assigned_by_user: Mapped["User"] = relationship("User", foreign_keys=[assigned_by])


class LabReport(Base):
    __tablename__ = "lab_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("lab_orders.id"))
    result_id: Mapped[int] = mapped_column(ForeignKey("lab_results.id"))
    approved_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order: Mapped["LabOrder"] = relationship("LabOrder")
    result: Mapped["LabResult"] = relationship("LabResult")
    approved_by_user: Mapped["User"] = relationship("User", foreign_keys=[approved_by])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[str]] = mapped_column(String(50))
    details: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FollowUpRequest(Base):
    __tablename__ = "follow_up_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    requested_date: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(Text)
    department: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    booked_visit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("opd_visits.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    patient: Mapped["Patient"] = relationship("Patient")
    doctor: Mapped["User"] = relationship("User")
    booked_visit: Mapped[Optional["OpdVisit"]] = relationship("OpdVisit")
