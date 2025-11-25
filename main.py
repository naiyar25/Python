from fastapi import FastAPI, Path, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Annotated,Literal, Optional
import json

class Patient(BaseModel):
    id: Annotated[str, Field(..., description="ID of the patient", example = "P001")]
    name: Annotated[str, Field(..., description="Name of the patient")]
    city: Annotated[str, Field(..., description="City of the patient")]
    age: Annotated[int, Field(..., gt=0, lt=120, description="Age of the patient in years")]
    gender: Annotated[ Literal['male','female', 'Other'], Field(...,description='gender of the patient')]
    height: Annotated[float, Field(..., gt=0, description="Height of the patient in meters")]
    weight: Annotated[float, Field(..., gt=0, description="Weight of the patient in KG")]

    @computed_field
    @property
    def bmi(self) -> float:
        bmi = round(self.weight / (self.height ** 2), 2)
        return bmi
    
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
    gender: Annotated[Optional[Literal['male','female',]], Field(default=None)]
    height: Annotated[Optional[float], Field(default=None, gt=0)]
    weight: Annotated[Optional[float], Field(default=None, gt=0)]   

  

app = FastAPI()

def load_data():
    with open("patients.json", "r") as f:
        data = json.load(f)
    return data

def save_data(data):
    with open("patients.json", "w") as f:
        json.dump(data, f)

@app.get('/')
def hello():
    return {"message": "Patient management syatem API"}

@app.get('/about')
def about():
    return {"message": "A fully functional API to manage your patients ."}

@app.get('/view')
def view():
    data = load_data()
    return data

@app.get('/patient/{patient_id}')
def viwe_patient(patient_id: str=Path(..., description='The ID of the patient in the DB', example='P001')):
    # load all the patients data
    data = load_data()
    if patient_id in data:
        return data[patient_id]
    raise HTTPException(status_code=404, detail="Patient not found")

@app.get('/sort')
def sort_patients(sort_by: str = Query(..., description= 'sort on the basis of height, weight and bmi'), order: str = Query('asc', description='sort by ascending or decending order')):
    valid_fields=['height', 'weight', 'bmi']
    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort field. Must be one of {valid_fields}")
    
    if order not in ['asc', 'desc']:
        raise HTTPException(status_code=400, detail="Invalid order. Must be 'asc' or 'desc'")   
    
    data= load_data()
    sort_order= True if order=='desc' else False
    sorted_data= sorted(data.values(), key=lambda x: x.get(sort_by, 0), reverse= sort_order)
    return sorted_data

@app.post('/create')
def create_patient(patient: Patient):
    # load all the patients data
    data = load_data()

    # check if patient already exists
    if patient.id in data:
        raise HTTPException(status_code=400, detail="Patient with this ID already exists")
    
    # New patient add to data.
    data[patient.id]= patient.model_dump(exclude=['id'])

    # save into the SON file
    save_data(data)
    return JSONResponse(content={"message": "Patient created successfully"}, status_code=201)



@app.put('/update/{patient_id}')
def update_patient(patient_id: str, patient_update: PatientUpdate):

    data= load_data()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")
    existing_patient_info= data[patient_id]
    updated_patient_info= patient_update.model_dump(exclude_unset=True)

    for key, value in updated_patient_info.items():
        existing_patient_info[key]= value
    
    #existing patient info -> pydantic object -> update bmi and verdict
    existing_patient_info ['id']= patient_id 
    patient_pydantic_obect= Patient(**existing_patient_info)

    # pydantic obect -> dict excluding Id
    patient_pydantic_obect.model_dump(exclude=['id'])

   # Add this data to dict
    existing_patient_info = data[patient_id]= existing_patient_info

    # save into the JSON file
    save_data(data)

    return JSONResponse (content={"message": "Patient updated successfully"}, status_code=200)


@app.delete('/delete/{patient_id}')
def delete_patient(patient_id: str):
    # Load data
    data= load_data()
    if patient_id not in data:
        raise HTTPException (status_code = 404, detail="Patient not found")
                             
    # delete patient
    del data[patient_id]

    # save into the JSON file
    save_data(data) 
    return JSONResponse (content={"message": "Patient deleted successfully"}, status_code=200)  


    




    