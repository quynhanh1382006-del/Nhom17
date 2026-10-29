from datetime import date, datetime, timedelta
from typing import Optional, Literal
import os, secrets
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, inspect
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY=os.getenv("SECRET_KEY","").strip()
if not SECRET_KEY or SECRET_KEY.casefold().startswith("change_me_"):
    raise RuntimeError(
        "SECRET_KEY is required. Set a strong, unique value in the environment or .env file."
    )

from database import Base, engine, get_db
from models import User, Pet, CareRecord, CareSchedule, Invoice, Notification, AIChat, Service
from services.ai_service import ask_care_ai, create_reminder_message, summarize_pet

app=FastAPI(title="Hệ thống quản lý thú cưng & lịch chăm sóc tích hợp AI", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
Base.metadata.create_all(bind=engine)
if "service_id" not in {column["name"] for column in inspect(engine).get_columns("care_schedules")}:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE care_schedules ADD COLUMN service_id INTEGER "
            "REFERENCES services(id) ON DELETE SET NULL"
        )

ALGORITHM=os.getenv("ALGORITHM","HS256")
EXPIRE=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES","1440"))
pwd=CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth=OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class RegisterIn(BaseModel):
    email: EmailStr
    password: str=Field(min_length=6)
    full_name: str=Field(min_length=2,max_length=150)
class PetIn(BaseModel):
    name:str; species:str; breed:str=""; gender:str=""; birth_date:Optional[date]=None; weight:Optional[float]=None; phone_note:str=""; medical_note:str=""; owner_id:Optional[int]=None
class CareRecordIn(BaseModel):
    pet_id:int; care_type:str; care_date:date; description:str=""; provider:str=""; next_due_date:Optional[date]=None; cost:float=0
class ScheduleIn(BaseModel):
    pet_id:int; care_type:str; scheduled_date:date; reminder_days:int=3; notes:str=""; status:str="pending"; service_id:Optional[int]=None
class InvoiceIn(BaseModel):
    pet_id:int; issued_date:date; total_amount:float=0; payment_status:str="unpaid"; notes:str=""
class AIChatIn(BaseModel):
    pet_id:Optional[int]=None; question:str=Field(min_length=2,max_length=3000)
class ServiceIn(BaseModel):
    name:str=Field(min_length=1,max_length=150)
    description:str=""
    price:float=Field(ge=0)
    duration_minutes:int=Field(gt=0)
    status:Literal["active","inactive"]="active"

def token(user):
    return jwt.encode({"sub":str(user.id),"role":user.role,"exp":datetime.utcnow()+timedelta(minutes=EXPIRE)},SECRET_KEY,algorithm=ALGORITHM)

def current_user(db:Session=Depends(get_db), token_value:str=Depends(oauth)):
    try:
        data=jwt.decode(token_value,SECRET_KEY,algorithms=[ALGORITHM]); uid=int(data["sub"])
    except (JWTError,KeyError,ValueError): raise HTTPException(401,"Token không hợp lệ")
    user=db.get(User,uid)
    if not user or user.status!="active": raise HTTPException(401,"Tài khoản không hoạt động")
    return user

def staff(user=Depends(current_user)):
    if user.role not in {"admin","reception","caregiver"}: raise HTTPException(403,"Chức năng yêu cầu quyền quản lý")
    return user

def admin_user(user=Depends(current_user)):
    if user.role!="admin": raise HTTPException(403,"Chỉ admin được quản lý dịch vụ")
    return user

def owner_pet(db, pet_id, user, allow_staff=True):
    pet=db.get(Pet,pet_id)
    if not pet: raise HTTPException(404,"Không tìm thấy thú cưng")
    if pet.owner_id!=user.id and not (allow_staff and user.role in {"admin","reception","caregiver"}): raise HTTPException(403,"Không có quyền truy cập")
    return pet

def pet_out(p):
    return {"id":p.id,"owner_id":p.owner_id,"name":p.name,"species":p.species,"breed":p.breed,"gender":p.gender,"birth_date":p.birth_date,"weight":p.weight,"phone_note":p.phone_note,"medical_note":p.medical_note}

def schedule_out(s):
    return {"id":s.id,"pet_id":s.pet_id,"pet_name":s.pet.name if s.pet else "","care_type":s.care_type,"scheduled_date":s.scheduled_date,"status":s.status,"reminder_days":s.reminder_days,"notes":s.notes,"service_id":s.service_id,"service_name":s.service.name if s.service else None}

def service_out(service):
    return {"id":service.id,"name":service.name,"description":service.description,"price":service.price,"duration_minutes":service.duration_minutes,"status":service.status}

def ai_json_response(content):
    return JSONResponse(
        content=jsonable_encoder(content),
        headers={"Content-Type":"application/json; charset=utf-8"},
    )

def create_notifications(db,user_id):
    today=date.today(); schedules=db.query(CareSchedule).join(Pet).filter(Pet.owner_id==user_id,CareSchedule.status=="pending").all()
    created=[]
    for s in schedules:
        if s.scheduled_date < today:
            s.status="missed"
            msg=f"{s.pet.name}: lịch {s.care_type} ngày {s.scheduled_date.strftime('%d/%m/%Y')} đã bị bỏ sót."
            exists=db.query(Notification).filter(Notification.user_id==user_id,Notification.kind=="missed",Notification.message==msg).first()
            if not exists:
                n=Notification(user_id=user_id,title="Cảnh báo bỏ sót lịch chăm sóc",message=msg,kind="missed"); db.add(n); created.append(n)
        elif (s.scheduled_date-today).days <= s.reminder_days:
            msg=f"{s.pet.name}: sắp đến lịch {s.care_type} vào ngày {s.scheduled_date.strftime('%d/%m/%Y')}."
            exists=db.query(Notification).filter(Notification.user_id==user_id,Notification.kind=="reminder",Notification.message==msg).first()
            if not exists:
                n=Notification(user_id=user_id,title="Nhắc lịch chăm sóc",message=msg,kind="reminder"); db.add(n); created.append(n)
    db.commit(); return created

@app.on_event("startup")
def startup():
    db=next(get_db())
    admin_email=os.getenv("ADMIN_EMAIL","admin@gmail.com")
    if not db.query(User).filter_by(email=admin_email).first():
        admin_password=os.getenv("ADMIN_PASSWORD","").strip()
        if not admin_password or admin_password.casefold().startswith("change_me_"):
            db.close()
            raise RuntimeError(
                "ADMIN_PASSWORD must be set to a strong, unique value before creating the initial admin account."
            )
        db.add(User(email=admin_email,password_hash=pwd.hash(admin_password),full_name=os.getenv("ADMIN_NAME","Quản trị viên"),role="admin")); db.commit()
    db.close()

@app.post("/api/auth/register")
def register(body:RegisterIn,db:Session=Depends(get_db)):
    if db.query(User).filter_by(email=body.email.lower()).first(): raise HTTPException(400,"Email đã tồn tại")
    u=User(email=body.email.lower(),password_hash=pwd.hash(body.password),full_name=body.full_name,role="user"); db.add(u); db.commit(); db.refresh(u)
    return {"access_token":token(u),"token_type":"bearer"}

@app.post("/api/auth/login")
def login(form:OAuth2PasswordRequestForm=Depends(),db:Session=Depends(get_db)):
    u=db.query(User).filter_by(email=form.username.lower()).first()
    if not u or not pwd.verify(form.password,u.password_hash): raise HTTPException(401,"Sai email hoặc mật khẩu")
    return {"access_token":token(u),"token_type":"bearer"}

@app.get("/api/auth/me")
def me(user=Depends(current_user)): return {"id":user.id,"email":user.email,"full_name":user.full_name,"role":user.role}

@app.get("/api/pets")
def list_pets(user=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(Pet)
    if user.role=="user": q=q.filter(Pet.owner_id==user.id)
    return [pet_out(p) for p in q.order_by(Pet.id.desc()).all()]

@app.get("/api/services")
def list_services(search:Optional[str]=Query(None),user=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(Service)
    if user.role=="user":
        q=q.filter(Service.status=="active")
    if search and search.strip():
        q=q.filter(Service.name.ilike(f"%{search.strip()}%"))
    return [service_out(service) for service in q.order_by(Service.name.asc()).all()]

@app.post("/api/services")
def create_service(body:ServiceIn,user=Depends(admin_user),db:Session=Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(422,"Tên dịch vụ không được để trống")
    service=Service(**body.model_dump(exclude={"name"}),name=body.name.strip())
    db.add(service); db.commit(); db.refresh(service)
    return service_out(service)

@app.put("/api/services/{service_id}")
def update_service(service_id:int,body:ServiceIn,user=Depends(admin_user),db:Session=Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(422,"Tên dịch vụ không được để trống")
    service=db.get(Service,service_id)
    if not service:
        raise HTTPException(404,"Không tìm thấy dịch vụ")
    for key,value in body.model_dump().items():
        setattr(service,key,value.strip() if key=="name" else value)
    db.commit(); db.refresh(service)
    return service_out(service)

@app.delete("/api/services/{service_id}")
def delete_service(service_id:int,user=Depends(admin_user),db:Session=Depends(get_db)):
    service=db.get(Service,service_id)
    if not service:
        raise HTTPException(404,"Không tìm thấy dịch vụ")
    if db.query(CareSchedule).filter_by(service_id=service.id).first():
        service.status="inactive"
        db.commit()
        return {"message":"Dịch vụ đang được lịch chăm sóc sử dụng nên đã được chuyển sang ngừng hoạt động","deactivated":True}
    db.delete(service); db.commit()
    return {"message":"Đã xóa dịch vụ","deactivated":False}

@app.get("/api/owners")
def list_owners(search:Optional[str]=Query(None),user=Depends(staff),db:Session=Depends(get_db)):
    q=db.query(User).filter(User.role=="user",User.status=="active")
    if search and search.strip():
        term=f"%{search.strip()}%"
        q=q.filter(or_(User.email.ilike(term),User.full_name.ilike(term)))
    owners=q.order_by(User.full_name.asc()).all()
    return [{"id":o.id,"email":o.email,"full_name":o.full_name,"pet_count":len(o.pets)} for o in owners]

@app.get("/api/owners/{owner_id}/pets")
def owner_pets(owner_id:int,user=Depends(staff),db:Session=Depends(get_db)):
    owner=db.get(User,owner_id)
    if not owner or owner.role!="user" or owner.status!="active":
        raise HTTPException(404,"Không tìm thấy chủ nuôi hợp lệ")
    return [pet_out(p) for p in db.query(Pet).filter_by(owner_id=owner.id).order_by(Pet.id.desc()).all()]

@app.post("/api/pets")
def create_pet(body:PetIn,user=Depends(current_user),db:Session=Depends(get_db)):
    if user.role=="user":
        owner_id=user.id
    else:
        if body.owner_id is None:
            raise HTTPException(422,"Vui lòng chọn chủ nuôi")
        owner=db.get(User,body.owner_id)
        if not owner or owner.role!="user" or owner.status!="active":
            raise HTTPException(404,"Không tìm thấy chủ nuôi hợp lệ")
        owner_id=owner.id
    pet_data=body.model_dump(exclude={"owner_id"})
    p=Pet(owner_id=owner_id,**pet_data); db.add(p); db.commit(); db.refresh(p); return pet_out(p)

@app.put("/api/pets/{pet_id}")
def update_pet(pet_id:int,body:PetIn,user=Depends(current_user),db:Session=Depends(get_db)):
    p=owner_pet(db,pet_id,user); [setattr(p,k,v) for k,v in body.model_dump(exclude={"owner_id"}).items()]; db.commit(); return pet_out(p)

@app.delete("/api/pets/{pet_id}")
def delete_pet(pet_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    p=owner_pet(db,pet_id,user); db.delete(p); db.commit(); return {"message":"Đã xóa thú cưng"}

@app.get("/api/care-records")
def list_records(pet_id:Optional[int]=None,user=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(CareRecord).join(Pet)
    if user.role=="user": q=q.filter(Pet.owner_id==user.id)
    if pet_id: q=q.filter(CareRecord.pet_id==pet_id)
    return [{"id":r.id,"pet_id":r.pet_id,"pet_name":r.pet.name,"care_type":r.care_type,"care_date":r.care_date,"description":r.description,"provider":r.provider,"next_due_date":r.next_due_date,"cost":r.cost} for r in q.order_by(CareRecord.care_date.desc()).all()]

@app.post("/api/care-records")
def create_record(body:CareRecordIn,user=Depends(current_user),db:Session=Depends(get_db)):
    owner_pet(db,body.pet_id,user); r=CareRecord(**body.model_dump()); db.add(r); db.commit(); db.refresh(r); return {"id":r.id,"message":"Đã lưu hồ sơ chăm sóc"}

@app.delete("/api/care-records/{record_id}")
def delete_record(record_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(CareRecord,record_id)
    if not r: raise HTTPException(404,"Không tìm thấy hồ sơ")
    owner_pet(db,r.pet_id,user); db.delete(r); db.commit(); return {"message":"Đã xóa"}

@app.get("/api/schedules")
def list_schedules(pet_id:Optional[int]=None,user=Depends(current_user),db:Session=Depends(get_db)):
    create_notifications(db,user.id)
    q=db.query(CareSchedule).join(Pet)
    if user.role=="user": q=q.filter(Pet.owner_id==user.id)
    if pet_id: q=q.filter(CareSchedule.pet_id==pet_id)
    return [schedule_out(s) for s in q.order_by(CareSchedule.scheduled_date.asc()).all()]

@app.post("/api/schedules")
def create_schedule(body:ScheduleIn,user=Depends(current_user),db:Session=Depends(get_db)):
    owner_pet(db,body.pet_id,user)
    if body.service_id is not None:
        service=db.get(Service,body.service_id)
        if not service or service.status!="active":
            raise HTTPException(404,"Không tìm thấy dịch vụ đang hoạt động")
    s=CareSchedule(**body.model_dump()); db.add(s); db.commit(); db.refresh(s); return schedule_out(s)

@app.put("/api/schedules/{schedule_id}/done")
def complete_schedule(schedule_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    s=db.get(CareSchedule,schedule_id)
    if not s: raise HTTPException(404,"Không tìm thấy lịch")
    owner_pet(db,s.pet_id,user); s.status="done"; db.commit(); return schedule_out(s)

@app.put("/api/schedules/{schedule_id}/missed")
def missed_schedule(schedule_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    s=db.get(CareSchedule,schedule_id)
    if not s: raise HTTPException(404,"Không tìm thấy lịch")
    owner_pet(db,s.pet_id,user); s.status="missed"; db.commit(); return schedule_out(s)

@app.get("/api/invoices")
def list_invoices(user=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(Invoice).filter(Invoice.owner_id==user.id).order_by(Invoice.issued_date.desc()).all() if user.role=="user" else db.query(Invoice).order_by(Invoice.issued_date.desc()).all()
    return [{"id":i.id,"invoice_code":i.invoice_code,"pet_id":i.pet_id,"pet_name":i.pet.name,"issued_date":i.issued_date,"total_amount":i.total_amount,"payment_status":i.payment_status,"notes":i.notes} for i in q]

@app.post("/api/invoices")
def create_invoice(body:InvoiceIn,user=Depends(staff),db:Session=Depends(get_db)):
    p=db.get(Pet,body.pet_id)
    if not p: raise HTTPException(404,"Không tìm thấy thú cưng")
    code="HD-"+datetime.now().strftime("%Y%m%d%H%M%S")+secrets.token_hex(2).upper()
    i=Invoice(owner_id=p.owner_id,invoice_code=code,**body.model_dump()); db.add(i); db.commit(); db.refresh(i); return {"id":i.id,"invoice_code":i.invoice_code}

@app.put("/api/invoices/{invoice_id}/paid")
def pay_invoice(invoice_id:int,user=Depends(staff),db:Session=Depends(get_db)):
    i=db.get(Invoice,invoice_id)
    if not i: raise HTTPException(404,"Không tìm thấy hóa đơn")
    i.payment_status="paid"; db.commit(); return {"message":"Đã cập nhật thanh toán"}

@app.get("/api/notifications")
def notifications(user=Depends(current_user),db:Session=Depends(get_db)):
    create_notifications(db,user.id)
    return [{"id":n.id,"title":n.title,"message":n.message,"kind":n.kind,"is_read":n.is_read,"created_at":n.created_at} for n in db.query(Notification).filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(30).all()]

@app.put("/api/notifications/{nid}/read")
def read_notification(nid:int,user=Depends(current_user),db:Session=Depends(get_db)):
    n=db.query(Notification).filter_by(id=nid,user_id=user.id).first()
    if not n: raise HTTPException(404,"Không tìm thấy thông báo")
    n.is_read=True; db.commit(); return {"message":"ok"}

@app.get("/api/dashboard")
def dashboard(user=Depends(current_user),db:Session=Depends(get_db)):
    create_notifications(db,user.id)
    pets=db.query(Pet).count()
    records=db.query(CareRecord).count()
    schedules=db.query(CareSchedule).count()
    missed=db.query(CareSchedule).filter(
        CareSchedule.scheduled_date<date.today(),
        func.lower(CareSchedule.status).notin_(("done","completed"))
    ).count()
    unpaid=db.query(Invoice).filter(Invoice.payment_status=="unpaid").count()
    return {"pets":pets,"care_records":records,"schedules":schedules,"missed_schedules":missed,"unpaid_invoices":unpaid}

@app.post("/api/ai/chat")
def ai_chat(body:AIChatIn,user=Depends(current_user),db:Session=Depends(get_db)):
    pet=None
    if body.pet_id is not None: pet=owner_pet(db,body.pet_id,user,allow_staff=True)
    elif user.role=="user": pet=db.query(Pet).filter_by(owner_id=user.id).order_by(Pet.id.desc()).first()
    records=[]; schedules=[]
    if pet:
        records=db.query(CareRecord).filter_by(pet_id=pet.id).order_by(CareRecord.care_date.asc()).all()
        schedules=db.query(CareSchedule).filter_by(pet_id=pet.id).order_by(CareSchedule.scheduled_date.asc()).all()
    answer,source=ask_care_ai(body.question,pet,records,schedules)
    chat=AIChat(user_id=user.id,pet_id=pet.id if pet else None,question=body.question,answer=answer,source=source); db.add(chat); db.commit()
    return ai_json_response({"answer":answer,"source":source,"pet_id":pet.id if pet else None})

@app.post("/api/ai/summary/{pet_id}")
def ai_summary(pet_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    pet=owner_pet(db,pet_id,user); records=db.query(CareRecord).filter_by(pet_id=pet.id).order_by(CareRecord.care_date.asc()).all(); schedules=db.query(CareSchedule).filter_by(pet_id=pet.id).order_by(CareSchedule.scheduled_date.asc()).all()
    answer,source=summarize_pet(pet,records,schedules)
    return ai_json_response({"summary":answer,"source":source})

@app.post("/api/ai/reminder/{schedule_id}")
def ai_reminder(schedule_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    schedule=db.get(CareSchedule,schedule_id)
    if not schedule:
        raise HTTPException(404,"Không tìm thấy lịch chăm sóc")
    pet=owner_pet(db,schedule.pet_id,user)
    message,source=create_reminder_message(schedule,pet)
    return ai_json_response({"message":message,"source":source,"schedule_id":schedule.id})

@app.get("/api/ai/history")
def ai_history(user=Depends(current_user),db:Session=Depends(get_db)):
    history=[{"id":c.id,"pet_id":c.pet_id,"question":c.question,"answer":c.answer,"source":c.source,"created_at":c.created_at} for c in db.query(AIChat).filter_by(user_id=user.id).order_by(AIChat.created_at.desc()).limit(50).all()]
    return ai_json_response(history)

@app.get("/api/admin/users")
def admin_users(user=Depends(staff),db:Session=Depends(get_db)):
    return [{"id":u.id,"email":u.email,"full_name":u.full_name,"role":u.role,"status":u.status,"pet_count":db.query(Pet).filter_by(owner_id=u.id).count()} for u in db.query(User).order_by(User.id.desc()).all()]

@app.put("/api/admin/users/{uid}/role")
def admin_role(uid:int,role:str,user=Depends(staff),db:Session=Depends(get_db)):
    if user.role!="admin": raise HTTPException(403,"Chỉ admin được phân quyền")
    if role not in {"user","admin","reception","caregiver"}: raise HTTPException(400,"Role không hợp lệ")
    u=db.get(User,uid)
    if not u: raise HTTPException(404,"Không tìm thấy user")
    u.role=role; db.commit(); return {"message":"Đã cập nhật quyền"}

@app.get("/")
def root(): return FileResponse("static/index.html")
@app.get("/login")
def login_page(): return FileResponse("static/login.html")
