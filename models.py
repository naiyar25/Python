from sqlalchemy import Column, Integer, String, Float
from database import Base

class Patient(Base):
    __tablename__ = "patients"

    # We use String for ID because your IDs are "P001", not integers
    id = Column(String, primary_key=True, index=True) 
    name = Column(String)
    city = Column(String)
    age = Column(Integer)
    gender = Column(String)
    height = Column(Float)
    weight = Column(Float)
    bmi = Column(Float)
    verdict = Column(String)