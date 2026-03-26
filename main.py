from fastapi import FastAPI, Path, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal, Optional
from sqlalchemy.orm import Session
import models
from database import engine, SessionLocal

# 1. Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- Dependency ---
# This opens a fresh database connection for every request and closes it after
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models (Validation) ---
class PatientDTO(BaseModel):
    id: Annotated[str, Field(..., description="ID of the patient", example="P001")]
    name: Annotated[str, Field(..., description="Name of the patient")]
    city: Annotated[str, Field(..., description="City of the patient")]
    age: Annotated[int, Field(..., gt=0, lt=120, description="Age of the patient in years")]
    gender: Annotated[Literal['male', 'female', 'Other'], Field(..., description='gender of the patient')]
    height: Annotated[float, Field(..., gt=0, description="Height of the patient in meters")]
    weight: Annotated[float, Field(..., gt=0, description="Weight of the patient in KG")]

    # We keep your logic here to calculate BMI automatically
    @computed_field
    @property
    def bmi(self) -> float:
        return round(self.weight / (self.height ** 2), 2)
    
    @computed_field
    @property
    def verdict(self) -> str:
        if self.bmi < 18.5:
            return "Underweight"
        elif 18.5 <= self.bmi < 24.9:
            return "Normal weight"
        elif 25 <= self.bmi < 29.9:
            return "Overweight"
        else:
            return "Obesity"

class PatientUpdate(BaseModel):
    name: Annotated[Optional[str], Field(default=None)]
    city: Annotated[Optional[str], Field(default=None)]
    age: Annotated[Optional[int], Field(default=None, gt=0, lt=120)]
    gender: Annotated[Optional[Literal['male', 'female', 'Other']], Field(default=None)]
    height: Annotated[Optional[float], Field(default=None, gt=0)]
    weight: Annotated[Optional[float], Field(default=None, gt=0)]   


# --- Routes ---

@app.get('/')
def hello():
    return {"message": "Patient management system API (SQL Version)"}

@app.get('/about')
def about():
    return {"message": "A fully functional API to manage your patients using SQLite."}

@app.get('/view')
def view(db: Session = Depends(get_db)):
    # SQL Query: SELECT * FROM patients
    patients = db.query(models.Patient).all()
    return patients

@app.get('/patient/{patient_id}')
def view_patient(
    patient_id: str = Path(..., description='The ID of the patient in the DB', example='P001'),
    db: Session = Depends(get_db)
):
    # SQL Query: SELECT * FROM patients WHERE id = patient_id
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@app.get('/sort')
def sort_patients(
    sort_by: str = Query(..., description='sort on the basis of height, weight and bmi'), 
    order: str = Query('asc', description='sort by ascending or decending order'),
    db: Session = Depends(get_db)
):
    valid_fields = ['height', 'weight', 'bmi']
    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort field. Must be one of {valid_fields}")
    
    if order not in ['asc', 'desc']:
        raise HTTPException(status_code=400, detail="Invalid order. Must be 'asc' or 'desc'")   
    
    # We fetch all data and sort in Python to match your exact previous logic
    # (SQL can do this too with order_by, but this preserves your logic perfectly)
    patients = db.query(models.Patient).all()
    
    # Convert SQL objects to dictionary-like objects for sorting if needed, 
    # or just sort the objects based on the attribute
    sort_order = True if order == 'desc' else False
    
    # We use getattr() to dynamically get the field (e.g., patient.height)
    sorted_data = sorted(patients, key=lambda x: getattr(x, sort_by), reverse=sort_order)
    return sorted_data

@app.post('/create')
def create_patient(patient: PatientDTO, db: Session = Depends(get_db)):
    # Check if exists
    existing_patient = db.query(models.Patient).filter(models.Patient.id == patient.id).first()
    if existing_patient:
        raise HTTPException(status_code=400, detail="Patient with this ID already exists")
    
    # Convert Pydantic model to Dict (this includes the computed bmi and verdict!)
    patient_data = patient.model_dump()
    
    # Create SQL Model
    db_patient = models.Patient(**patient_data)
    
    # Add and Commit
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    
    return JSONResponse(content={"message": "Patient created successfully"}, status_code=201)

@app.put('/update/{patient_id}')
def update_patient(patient_id: str, patient_update: PatientUpdate, db: Session = Depends(get_db)):
    # Find patient
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get the data the user sent (excluding None values)
    update_data = patient_update.model_dump(exclude_unset=True)

    # Update the SQL object attributes
    for key, value in update_data.items():
        setattr(db_patient, key, value)
    
    # --- Recalculate Logic ---
    # Because height/weight might have changed, we must update BMI and Verdict.
    # We can reuse your Pydantic logic for this.
    
    # 1. Create a dictionary of the current state of the database object
    current_data = {
        "id": db_patient.id,
        "name": db_patient.name,
        "city": db_patient.city,
        "age": db_patient.age,
        "gender": db_patient.gender,
        "height": db_patient.height,
        "weight": db_patient.weight
    }
    
    # 2. Pass it through Pydantic to run the @computed_field logic
    # We ignore the computed fields in input, let Pydantic regenerate them
    temp_patient_model = PatientDTO(**current_data)
    
    # 3. Save the new calculations back to the Database object
    db_patient.bmi = temp_patient_model.bmi
    db_patient.verdict = temp_patient_model.verdict

    db.commit()
    db.refresh(db_patient)

    return JSONResponse(content={"message": "Patient updated successfully"}, status_code=200)

@app.delete('/delete/{patient_id}')
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
                             
    db.delete(db_patient)
    db.commit()
    
    return JSONResponse(content={"message": "Patient deleted successfully"}, status_code=200)