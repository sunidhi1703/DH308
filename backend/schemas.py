from datetime import datetime, date
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from models import UserRole, VisitStatus, OrderStatus, SampleStatus, ResultStatus, Priority, AbhaStatus


# ── Auth ──────────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
    full_name: str


# ── User ──────────────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    model_config = {"from_attributes": True}


# ── Patient ───────────────────────────────────────────────────────────────────
class PatientCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    dob: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    abha_number: Optional[str] = None


class PatientOut(BaseModel):
    id: int
    uhid: str
    full_name: str
    dob: Optional[str]
    gender: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    blood_group: Optional[str]
    allergies: Optional[str]
    abha_number: Optional[str]
    abha_status: AbhaStatus
    created_at: datetime
    model_config = {"from_attributes": True}


# ── OPD Visit ─────────────────────────────────────────────────────────────────
class VisitCreate(BaseModel):
    patient_id: int
    doctor_id: int
    department: Optional[str] = "General Medicine"
    appointment_time: Optional[datetime] = None


class VisitOut(BaseModel):
    id: int
    visit_id: str
    patient_id: int
    doctor_id: Optional[int]
    department: Optional[str]
    token_number: Optional[str]
    status: VisitStatus
    appointment_time: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}


class VisitDetail(VisitOut):
    patient: PatientOut
    doctor: Optional[UserOut]


# ── Vitals ────────────────────────────────────────────────────────────────────
class VitalsCreate(BaseModel):
    temperature: Optional[float] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    pulse: Optional[int] = Field(default=None, ge=1, le=300)
    spo2: Optional[float] = Field(default=None, ge=0, le=100)
    height_cm: Optional[float] = Field(default=None, gt=0)
    weight_kg: Optional[float] = Field(default=None, gt=0)
    chief_complaint: Optional[str] = None
    is_urgent: bool = False


class VitalsOut(BaseModel):
    id: int
    visit_id: int
    temperature: Optional[float]
    bp_systolic: Optional[int]
    bp_diastolic: Optional[int]
    pulse: Optional[int]
    spo2: Optional[float]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    chief_complaint: Optional[str]
    is_urgent: bool
    ready_for_doctor: bool
    recorded_at: datetime
    nurse: Optional[UserOut]
    model_config = {"from_attributes": True}


# ── Consultation ──────────────────────────────────────────────────────────────
class ConsultationCreate(BaseModel):
    complaints: Optional[str] = None
    examination: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None


class ConsultationOut(BaseModel):
    id: int
    visit_id: int
    doctor_id: int
    complaints: Optional[str]
    examination: Optional[str]
    diagnosis: Optional[str]
    notes: Optional[str]
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Prescription ──────────────────────────────────────────────────────────────
class PrescriptionCreate(BaseModel):
    medicine: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    advice: Optional[str] = None


class PrescriptionOut(BaseModel):
    id: int
    medicine: str
    dosage: Optional[str]
    frequency: Optional[str]
    duration: Optional[str]
    instructions: Optional[str]
    advice: Optional[str]
    model_config = {"from_attributes": True}


# ── Lab Test Catalogue ────────────────────────────────────────────────────────
class TestCatalogueOut(BaseModel):
    id: int
    code: str
    name: str
    category: Optional[str]
    sample_type: Optional[str]
    turnaround_minutes: int
    model_config = {"from_attributes": True}


# ── Lab Order ─────────────────────────────────────────────────────────────────
class LabOrderCreate(BaseModel):
    visit_id: int
    test_ids: List[int]
    priority: Priority = Priority.routine


class LabOrderTestOut(BaseModel):
    id: int
    test: TestCatalogueOut
    model_config = {"from_attributes": True}


class LabOrderOut(BaseModel):
    id: int
    order_id: str
    visit_id: int
    ordered_by: int
    priority: Priority
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    order_tests: List[LabOrderTestOut] = []
    model_config = {"from_attributes": True}


class LabOrderDetail(LabOrderOut):
    ordered_by_user: Optional[UserOut]
    technician_assignment: Optional[Any] = None


# ── Technician Assignment ─────────────────────────────────────────────────────
class AssignTechnicianRequest(BaseModel):
    order_id: int
    technician_id: int


class AssignReviewerRequest(BaseModel):
    result_id: int
    pathologist_id: int


# ── Sample ────────────────────────────────────────────────────────────────────
class SampleCollectRequest(BaseModel):
    order_id: int


class SampleRejectRequest(BaseModel):
    sample_id: int
    rejection_reason: str


class SampleOut(BaseModel):
    id: int
    sample_id: str
    order_id: int
    status: SampleStatus
    rejection_reason: Optional[str]
    barcode: Optional[str]
    collected_at: Optional[datetime]
    received_at: Optional[datetime]
    processed_at: Optional[datetime]
    model_config = {"from_attributes": True}


# ── Lab Result ────────────────────────────────────────────────────────────────
class LabResultOut(BaseModel):
    id: int
    sample_id: int
    test_id: int
    run_number: int
    value: Optional[str]
    unit: Optional[str]
    ref_range: Optional[str]
    flag: Optional[str]
    qc_status: Optional[str]
    analyser_flags: Optional[str]
    status: ResultStatus
    received_at: Optional[datetime]
    test: Optional[TestCatalogueOut]
    model_config = {"from_attributes": True}


# ── Review ────────────────────────────────────────────────────────────────────
class ReviewDecisionRequest(BaseModel):
    decision: str  # approved, held, rerun
    hold_reason: Optional[str] = None
    notification_recorded: bool = False


class ReviewAssignmentOut(BaseModel):
    id: int
    result_id: int
    pathologist_id: int
    assigned_at: datetime
    reviewed_at: Optional[datetime]
    decision: Optional[str]
    hold_reason: Optional[str]
    model_config = {"from_attributes": True}


# ── Lab Report ────────────────────────────────────────────────────────────────
class LabReportOut(BaseModel):
    id: int
    report_id: str
    order_id: int
    result_id: int
    approved_at: datetime
    approved_by_user: Optional[UserOut]
    result: Optional[LabResultOut]
    model_config = {"from_attributes": True}
