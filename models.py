from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Float, ForeignKey, Boolean, Index, CheckConstraint
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id=Column(Integer,primary_key=True,index=True)
    email=Column(String(255),unique=True,nullable=False,index=True)
    password_hash=Column(String(255),nullable=False)
    full_name=Column(String(150),nullable=False)
    role=Column(String(30),default="user",nullable=False) # user/admin/reception/caregiver
    status=Column(String(20),default="active",nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow)
    pets=relationship("Pet",back_populates="owner",cascade="all, delete-orphan")
    notifications=relationship("Notification",back_populates="user",cascade="all, delete-orphan")
    ai_chats=relationship("AIChat",back_populates="user",cascade="all, delete-orphan")

class Pet(Base):
    __tablename__="pets"
    id=Column(Integer,primary_key=True,index=True)
    owner_id=Column(Integer,ForeignKey("users.id",ondelete="CASCADE"),nullable=False,index=True)
    name=Column(String(100),nullable=False)
    species=Column(String(50),nullable=False)
    breed=Column(String(100),default="")
    gender=Column(String(20),default="")
    birth_date=Column(Date,nullable=True)
    weight=Column(Float,nullable=True)
    phone_note=Column(String(255),default="")
    medical_note=Column(Text,default="")
    created_at=Column(DateTime,default=datetime.utcnow)
    owner=relationship("User",back_populates="pets")
    care_records=relationship("CareRecord",back_populates="pet",cascade="all, delete-orphan")
    schedules=relationship("CareSchedule",back_populates="pet",cascade="all, delete-orphan")
    invoices=relationship("Invoice",back_populates="pet",cascade="all, delete-orphan")

class CareRecord(Base):
    __tablename__="care_records"
    id=Column(Integer,primary_key=True,index=True)
    pet_id=Column(Integer,ForeignKey("pets.id",ondelete="CASCADE"),nullable=False,index=True)
    care_type=Column(String(50),nullable=False) # vaccination/grooming/deworming/health_check/medication/other
    care_date=Column(Date,nullable=False)
    description=Column(Text,default="")
    provider=Column(String(150),default="")
    next_due_date=Column(Date,nullable=True)
    cost=Column(Float,default=0)
    created_at=Column(DateTime,default=datetime.utcnow)
    pet=relationship("Pet",back_populates="care_records")

class CareSchedule(Base):
    __tablename__="care_schedules"
    id=Column(Integer,primary_key=True,index=True)
    pet_id=Column(Integer,ForeignKey("pets.id",ondelete="CASCADE"),nullable=False,index=True)
    care_type=Column(String(50),nullable=False)
    scheduled_date=Column(Date,nullable=False,index=True)
    status=Column(String(20),default="pending",nullable=False) # pending/done/missed
    reminder_days=Column(Integer,default=3)
    notes=Column(Text,default="")
    service_id=Column(Integer,ForeignKey("services.id",ondelete="SET NULL"),nullable=True,index=True)
    pet=relationship("Pet",back_populates="schedules")
    service=relationship("Service",back_populates="schedules")

class Service(Base):
    __tablename__="services"
    __table_args__=(
        CheckConstraint("price >= 0",name="ck_services_price_nonnegative"),
        CheckConstraint("duration_minutes > 0",name="ck_services_duration_positive"),
        CheckConstraint("status IN ('active', 'inactive')",name="ck_services_status_valid"),
    )
    id=Column(Integer,primary_key=True,index=True)
    name=Column(String(150),nullable=False,index=True)
    description=Column(Text,nullable=False,default="")
    price=Column(Float,nullable=False)
    duration_minutes=Column(Integer,nullable=False)
    status=Column(String(20),nullable=False,default="active")
    schedules=relationship("CareSchedule",back_populates="service")

class Invoice(Base):
    __tablename__="invoices"
    id=Column(Integer,primary_key=True,index=True)
    owner_id=Column(Integer,ForeignKey("users.id",ondelete="CASCADE"),nullable=False,index=True)
    pet_id=Column(Integer,ForeignKey("pets.id",ondelete="CASCADE"),nullable=False,index=True)
    invoice_code=Column(String(50),unique=True,nullable=False)
    issued_date=Column(Date,nullable=False)
    total_amount=Column(Float,default=0)
    payment_status=Column(String(30),default="unpaid") # unpaid/paid
    notes=Column(Text,default="")
    pet=relationship("Pet",back_populates="invoices")

class Notification(Base):
    __tablename__="notifications"
    id=Column(Integer,primary_key=True,index=True)
    user_id=Column(Integer,ForeignKey("users.id",ondelete="CASCADE"),nullable=False,index=True)
    title=Column(String(200),nullable=False)
    message=Column(Text,nullable=False)
    kind=Column(String(40),default="care")
    is_read=Column(Boolean,default=False,index=True)
    created_at=Column(DateTime,default=datetime.utcnow,index=True)
    user=relationship("User",back_populates="notifications")

class AIChat(Base):
    __tablename__="ai_chats"
    id=Column(Integer,primary_key=True,index=True)
    user_id=Column(Integer,ForeignKey("users.id",ondelete="CASCADE"),nullable=False,index=True)
    pet_id=Column(Integer,ForeignKey("pets.id",ondelete="SET NULL"),nullable=True,index=True)
    question=Column(Text,nullable=False)
    answer=Column(Text,nullable=False)
    source=Column(String(30),default="AI")
    created_at=Column(DateTime,default=datetime.utcnow,index=True)
    user=relationship("User",back_populates="ai_chats")

Index("ix_care_pet_date", CareRecord.pet_id, CareRecord.care_date)
Index("ix_schedule_pet_date", CareSchedule.pet_id, CareSchedule.scheduled_date)
