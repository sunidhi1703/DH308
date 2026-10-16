from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from database import get_db
from models import (
    OpdVisit, Patient, Vitals, Consultation, Prescription, LabOrder,
    LabOrderTest, LabResult, LabReport, MedicalHistory, Sample, User,
    UserRole, VisitStatus, OrderStatus, AuditLog
)
from auth import require_role
from schemas import (
    ConsultationCreate, ConsultationOut, PrescriptionCreate, PrescriptionOut,
    LabOrderCreate, LabOrderOut, LabOrderDetail, LabReportOut,
    VitalsOut, TestCatalogueOut, VisitDetail, PatientOut
)
from models import LabTestCatalogue
from datetime import datetime
import random, string

router = APIRouter(prefix="/api/doctor", tags=["doctor"])
_require = require_role(UserRole.doctor)


def _gen_order_id(db: Session) -> str:
    while True:
        oid = "ORD-" + "".join(random.choices(string.digits, k=5))
        if not db.query(LabOrder).filter_by(order_id=oid).first():
            return oid


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(_require)):
    """Today's patients, pending lab orders, newly released reports."""
    my_visits = (
        db.query(OpdVisit)
        .options(joinedload(OpdVisit.patient))
        .filter(OpdVisit.doctor_id == current_user.id)
        .filter(OpdVisit.status.notin_([VisitStatus.completed, VisitStatus.cancelled]))
        .order_by(OpdVisit.created_at.desc())
        .limit(20)
        .all()
    )
    # Pending lab orders for my patients
    my_visit_ids = [v.id for v in db.query(OpdVisit).filter_by(doctor_id=current_user.id).all()]
    pending_orders = (
        db.query(LabOrder)
        .options(joinedload(LabOrder.order_tests).joinedload(LabOrderTest.test), joinedload(LabOrder.visit).joinedload(OpdVisit.patient))
        .filter(LabOrder.visit_id.in_(my_visit_ids))
        .filter(LabOrder.status != OrderStatus.completed)
        .order_by(LabOrder.created_at.desc())
        .all()
    )
    # Released reports
    released_reports = (
        db.query(LabReport)
        .options(
            joinedload(LabReport.result).joinedload(LabResult.test),
            joinedload(LabReport.order).joinedload(LabOrder.visit).joinedload(OpdVisit.patient),
            joinedload(LabReport.approved_by_user)
        )
        .filter(LabReport.order_id.in_([o.id for o in db.query(LabOrder).filter(LabOrder.visit_id.in_(my_visit_ids)).all()]))
        .order_by(LabReport.approved_at.desc())
        .limit(10)
        .all()
    )
    return {
        "my_patients": [
            {"visit_id": v.id, "visit_ref": v.visit_id, "token": v.token_number,
             "status": v.status.value, "patient": {"id": v.patient.id, "uhid": v.patient.uhid, "name": v.patient.full_name}}
            for v in my_visits
        ],
        "pending_order_items": [{"id": o.id, "order_id": o.order_id, "patient_id": o.visit.patient_id, "patient": o.visit.patient.full_name, "status": o.status.value} for o in pending_orders],
        "report_items": [{"report_id": r.report_id, "patient_id": r.order.visit.patient_id, "patient": r.order.visit.patient.full_name, "test": r.result.test.name} for r in released_reports],
        "pending_orders": len(pending_orders),
        "released_reports": len(released_reports),
    }


@router.get("/patients/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(_require)):
    """Get patient — only if they have a visit assigned to this doctor."""
    p = db.query(Patient).filter_by(id=patient_id).first()
    if not p:
        raise HTTPException(404, "Patient not found")
    visit = db.query(OpdVisit).filter(OpdVisit.patient_id == patient_id, OpdVisit.doctor_id == current_user.id).first()
    if not visit:
        raise HTTPException(403, "Not authorized to access this patient")
    return p


@router.get("/patients/{patient_id}/visits")
def patient_visits(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(_require)):
    authorized = db.query(OpdVisit).filter(OpdVisit.patient_id == patient_id, OpdVisit.doctor_id == current_user.id).first()
    if not authorized:
        raise HTTPException(403, "Not authorized")
    visits = (
        db.query(OpdVisit)
        .options(joinedload(OpdVisit.patient), joinedload(OpdVisit.doctor), joinedload(OpdVisit.vitals))
        .filter(OpdVisit.patient_id == patient_id)
        .order_by(OpdVisit.created_at.desc())
        .all()
    )
    result = []
    for v in visits:
        result.append({
            "id": v.id, "visit_id": v.visit_id, "status": v.status.value,
            "department": v.department, "appointment_time": v.appointment_time,
            "diagnosis": v.consultation.diagnosis if v.consultation else None,
            "notes": v.consultation.notes if v.consultation else None,
            "prescriptions": [{"medicine": p.medicine, "dosage": p.dosage, "frequency": p.frequency, "duration": p.duration, "instructions": p.instructions} for p in v.consultation.prescriptions] if v.consultation else [],
            "orders": [{"order_id": o.order_id, "status": o.status.value} for o in v.lab_orders],
            "conditions": [{"condition": h.condition, "medicines": h.current_medicines} for h in db.query(MedicalHistory).filter_by(patient_id=patient_id).all()],
            "doctor": {"id": v.doctor.id, "full_name": v.doctor.full_name} if v.doctor else None,
            "vitals": {
                "bp": f"{v.vitals.bp_systolic}/{v.vitals.bp_diastolic}",
                "pulse": v.vitals.pulse, "temp": v.vitals.temperature,
                "chief_complaint": v.vitals.chief_complaint, "is_urgent": v.vitals.is_urgent
            } if v.vitals else None,
        })
    return result


@router.get("/patients/{patient_id}/current-visit")
def current_visit(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(_require)):
    visit = (
        db.query(OpdVisit)
        .options(joinedload(OpdVisit.patient), joinedload(OpdVisit.vitals))
        .filter(
            OpdVisit.patient_id == patient_id,
            OpdVisit.doctor_id == current_user.id,
            OpdVisit.status.notin_([VisitStatus.completed, VisitStatus.cancelled])
        )
        .order_by(OpdVisit.created_at.desc())
        .first()
    )
    if not visit:
        raise HTTPException(404, "No active visit found")
    return {
        "id": visit.id, "visit_id": visit.visit_id, "status": visit.status.value,
        "token": visit.token_number, "department": visit.department,
        "vitals": {
            "temperature": visit.vitals.temperature, "bp_systolic": visit.vitals.bp_systolic,
            "bp_diastolic": visit.vitals.bp_diastolic, "pulse": visit.vitals.pulse,
            "spo2": visit.vitals.spo2, "height_cm": visit.vitals.height_cm, "weight_kg": visit.vitals.weight_kg,
            "chief_complaint": visit.vitals.chief_complaint, "is_urgent": visit.vitals.is_urgent
        } if visit.vitals else None
    }


@router.post("/visits/{visit_id}/consultation", response_model=ConsultationOut)
def save_consultation(
    visit_id: int, data: ConsultationCreate,
    db: Session = Depends(get_db), current_user: User = Depends(_require)
):
    visit = db.query(OpdVisit).filter_by(id=visit_id, doctor_id=current_user.id).first()
    if not visit:
        raise HTTPException(403, "Not authorized or visit not found")

    if visit.status in (VisitStatus.completed, VisitStatus.cancelled):
        raise HTTPException(400, "This visit is closed")
    existing = db.query(Consultation).filter_by(visit_id=visit_id).first()
    if existing:
        for k, v in data.model_dump().items():
            setattr(existing, k, v)
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    consult = Consultation(visit_id=visit_id, doctor_id=current_user.id, **data.model_dump())
    db.add(consult)
    visit.status = VisitStatus.in_consultation
    db.commit()
    db.refresh(consult)
    db.add(AuditLog(user_id=current_user.id, action="save_consultation", entity_type="visit", entity_id=str(visit_id)))
    db.commit()
    return consult


@router.get("/visits/{visit_id}/consultation", response_model=ConsultationOut)
def get_consultation(visit_id: int, db: Session = Depends(get_db), current_user: User = Depends(_require)):
    if not db.query(OpdVisit).filter_by(id=visit_id, doctor_id=current_user.id).first():
        raise HTTPException(403, "Not authorized for this visit")
    consult = db.query(Consultation).filter_by(visit_id=visit_id).first()
    if not consult:
        raise HTTPException(404, "No consultation recorded yet")
    return consult


@router.post("/visits/{visit_id}/prescriptions", response_model=List[PrescriptionOut])
def save_prescriptions(
    visit_id: int, items: List[PrescriptionCreate],
    db: Session = Depends(get_db), current_user: User = Depends(_require)
):
    if not db.query(OpdVisit).filter_by(id=visit_id, doctor_id=current_user.id).first():
        raise HTTPException(403, "Not authorized for this visit")
    consult = db.query(Consultation).filter_by(visit_id=visit_id).first()
    if not consult:
        raise HTTPException(404, "Consultation not found — save consultation first")
    # Replace prescriptions for this visit
    for p in consult.prescriptions:
        db.delete(p)
    db.flush()
    new_prescriptions = []
    for item in items:
        p = Prescription(consultation_id=consult.id, **item.model_dump())
        db.add(p)
        new_prescriptions.append(p)
    db.commit()
    return new_prescriptions


@router.get("/visits/{visit_id}/prescriptions", response_model=List[PrescriptionOut])
def get_prescriptions(visit_id: int, db: Session = Depends(get_db), current_user: User = Depends(_require)):
    if not db.query(OpdVisit).filter_by(id=visit_id, doctor_id=current_user.id).first():
        raise HTTPException(403, "Not authorized for this visit")
    consult = db.query(Consultation).filter_by(visit_id=visit_id).first()
    if not consult:
        return []
    return consult.prescriptions


@router.get("/catalogue", response_model=List[TestCatalogueOut])
def get_catalogue(db: Session = Depends(get_db), _=Depends(_require)):
    return db.query(LabTestCatalogue).all()


@router.post("/lab-orders", response_model=LabOrderOut)
def create_lab_order(
    data: LabOrderCreate,
    db: Session = Depends(get_db), current_user: User = Depends(_require)
):
    visit = db.query(OpdVisit).filter_by(id=data.visit_id, doctor_id=current_user.id).first()
    if not visit:
        raise HTTPException(403, "Not authorized or visit not found")

    if visit.status in (VisitStatus.completed, VisitStatus.cancelled):
        raise HTTPException(400, "Cannot order tests for a closed visit")
    if not data.test_ids or len(set(data.test_ids)) != len(data.test_ids):
        raise HTTPException(400, "Choose one or more distinct tests")
    order = LabOrder(
        order_id=_gen_order_id(db),
        visit_id=data.visit_id,
        ordered_by=current_user.id,
        priority=data.priority,
        status=OrderStatus.ordered,
    )
    db.add(order)
    db.flush()

    for tid in data.test_ids:
        test = db.query(LabTestCatalogue).filter_by(id=tid).first()
        if not test:
            raise HTTPException(404, f"Test {tid} not found")
        db.add(LabOrderTest(order_id=order.id, test_id=tid))

    db.commit()
    db.refresh(order)
    db.add(AuditLog(user_id=current_user.id, action="create_lab_order", entity_type="lab_order", entity_id=order.order_id))
    db.commit()
    return order


@router.get("/visits/{visit_id}/lab-orders")
def get_visit_lab_orders(visit_id: int, db: Session = Depends(get_db), current_user: User = Depends(_require)):
    visit = db.query(OpdVisit).filter_by(id=visit_id, doctor_id=current_user.id).first()
    if not visit:
        raise HTTPException(403, "Not authorized")
    orders = (
        db.query(LabOrder)
        .options(joinedload(LabOrder.order_tests).joinedload(LabOrderTest.test))
        .filter(LabOrder.visit_id == visit_id)
        .order_by(LabOrder.created_at.desc())
        .all()
    )
    result = []
    for o in orders:
        result.append({
            "id": o.id, "order_id": o.order_id, "priority": o.priority.value,
            "status": o.status.value, "created_at": o.created_at,
            "tests": [{"code": ot.test.code, "name": ot.test.name} for ot in o.order_tests],
        })
    return result


@router.get("/patients/{patient_id}/reports")
def get_patient_reports(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(_require)):
    authorized = db.query(OpdVisit).filter(OpdVisit.patient_id == patient_id, OpdVisit.doctor_id == current_user.id).first()
    if not authorized:
        raise HTTPException(403, "Not authorized")

    visit_ids = [v.id for v in db.query(OpdVisit).filter(OpdVisit.patient_id == patient_id).all()]
    order_ids = [o.id for o in db.query(LabOrder).filter(LabOrder.visit_id.in_(visit_ids)).all()]

    reports = (
        db.query(LabReport)
        .options(
            joinedload(LabReport.result).joinedload(LabResult.test),
            joinedload(LabReport.approved_by_user)
        )
        .filter(LabReport.order_id.in_(order_ids))
        .order_by(LabReport.approved_at.desc())
        .all()
    )
    result = []
    for r in reports:
        result.append({
            "report_id": r.report_id, "order_id": r.order_id,
            "approved_at": r.approved_at,
            "approved_by": r.approved_by_user.full_name if r.approved_by_user else None,
            "test": {"code": r.result.test.code, "name": r.result.test.name} if r.result and r.result.test else None,
            "value": r.result.value if r.result else None,
            "unit": r.result.unit if r.result else None,
            "ref_range": r.result.ref_range if r.result else None,
            "flag": r.result.flag if r.result else None,
        })
    return result


@router.post("/visits/{visit_id}/complete")
def complete_visit(visit_id: int, db: Session = Depends(get_db), current_user: User = Depends(_require)):
    visit = db.query(OpdVisit).filter_by(id=visit_id, doctor_id=current_user.id).first()
    if not visit:
        raise HTTPException(403, "Not authorized")
    visit.status = VisitStatus.completed
    db.commit()
    return {"message": "Visit completed"}


@router.get("/patients/{patient_id}/lab-orders")
def patient_orders(patient_id: int, db: Session = Depends(get_db), user: User = Depends(_require)):
    get_patient(patient_id, db, user)
    orders = db.query(LabOrder).join(OpdVisit).filter(OpdVisit.patient_id == patient_id).order_by(LabOrder.id.desc()).all()
    return [{"id": o.id, "order_id": o.order_id, "priority": o.priority.value, "status": o.status.value,
             "tests": [{"name": t.test.name} for t in o.order_tests]} for o in orders]


@router.get("/patients")
def my_patients(db: Session = Depends(get_db), user: User = Depends(_require)):
    patients = db.query(Patient).join(OpdVisit).filter(OpdVisit.doctor_id == user.id).distinct().all()
    return [{"id": p.id, "name": p.full_name, "uhid": p.uhid} for p in patients]
