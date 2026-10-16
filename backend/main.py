import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from database import engine
import models

models.Base.metadata.create_all(bind=engine)

with engine.begin() as connection:
    prescription_columns = {column["name"] for column in inspect(connection).get_columns("prescriptions")}
    for column in ("frequency", "duration"):
        if column not in prescription_columns:
            connection.execute(text(f"ALTER TABLE prescriptions ADD COLUMN {column} VARCHAR(100)"))

app = FastAPI(title="ClinSync", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip().rstrip("/") for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import auth, receptionist, nurse, doctor, coordinator, technician, pathologist

app.include_router(auth.router)
app.include_router(receptionist.router)
app.include_router(nurse.router)
app.include_router(doctor.router)
app.include_router(coordinator.router)
app.include_router(technician.router)
app.include_router(pathologist.router)


@app.get("/")
def root():
    return {"message": "ClinSync API", "docs": "/docs"}


@app.on_event("startup")
def recover_review_handoffs():
    from database import SessionLocal
    from review_routing import assign_received_results
    with SessionLocal() as db:
        assign_received_results(db)
        db.commit()

from routers import followups
app.include_router(followups.router)
