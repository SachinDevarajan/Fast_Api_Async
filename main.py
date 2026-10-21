from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pwdlib import PasswordHash
from starlette.concurrency import run_in_threadpool

import os
from dotenv import load_dotenv

from datetime import datetime, timedelta, timezone

from database import *
from models import *
from schemas import *

load_dotenv()

SECURITY_KEY = os.environ['SECURITY_KEY']
ALGORITHM = "HS256"

password_hash = PasswordHash.recommended()
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()

app = FastAPI(lifespan=lifespan)


async def get_current_user(creadentials : HTTPAuthorizationCredentials = Depends(security),
                     db: AsyncSession = Depends(get_db)):
    
    token = creadentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECURITY_KEY,
            algorithms=[ALGORITHM]
        )
        user_id = int(payload['sub'])

    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or Experid Token"
        )

    user = await db.get(UserDB, user_id)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User Not Found"
        )
    
    return user


def admin_required(user: UserDB = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return user

@app.get('/')
async def home():
    return {'message':"FastAPI async is running"}


@app.post('/students/', response_model=StudentOut)
async def create_student(data: StudentCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DepartmentDB).where(
            DepartmentDB.name == data.dept_name
        )
    )

    department = result.scalar_one_or_none()

    if department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    student = StudentDB(
        name=data.name,
        age=data.age,
        email=data.email,
        dept_id=department.id
    )

    db.add(student)
    await db.commit()
    await db.refresh(student)

    return student


@app.get('/students')
async def get_students(db: AsyncSession = Depends(get_db)):
    students = await db.scalars(select(StudentDB))

    return students.all()


@app.get('/students/{student_id}')
async def get_student(student_id : int, db: AsyncSession = Depends(get_db)):
    student = await db.get(StudentDB, student_id)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student Not Found"
        )

    return student

@app.put('/student/{student_id}')
async def update_student(student_id : int, data:StudentUpdate, 
                         db: AsyncSession = Depends(get_db)):
    student = await db.get(StudentDB, student_id)
    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student Not Found"
        )
    for field, value in data.model_dump().items():
        setattr(student,field,value)

    try:
        await db.commit()
        await db.refresh(student)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A student with this email already exists"
        )
    return student


'''
Login & Register
'''
@app.post('/register/')
async def register(data: UserCreate, db:AsyncSession = Depends(get_db)):
    res = await db.execute(select(UserDB).where(
        (UserDB.email == data.email) | (UserDB.username == data.username)
    ))

    existing_user = res.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email or username already present"
        )

    hashed = await run_in_threadpool(password_hash.hash,data.password)

    new_user = UserDB(
        username = data.username,
        email = data.email,
        password = hashed
    )

    db.add(new_user)

    try:
        await db.commit()
        await db.refresh(new_user)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email or Username already registered"
        )

    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email
    }


@app.post('/login/')
async def login(data:UserLogin, db:AsyncSession = Depends(get_db)):
    res = await db.execute(select(UserDB).where(UserDB.email == data.email))
    user = res.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401,detail='Invalid Email or password')

    is_valid = await run_in_threadpool(
        password_hash.verify,
        data.password,
        user.password
    )

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail='Invalid Email or Password'
        )

    access_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
            },
            SECURITY_KEY,
            algorithm=ALGORITHM
        )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.post('/departments',status_code=201)
async def create_dept(data : DeptCreate, db: AsyncSession = Depends(get_db),
                      admin : UserDB = Depends(admin_required)):
    dept = DepartmentDB(name = data.name, place = data.place)

    db.add(dept)
    await db.commit()
    await db.refresh(dept)

    return {
        'id': dept.id,
        'name': dept.name
    }



@app.post('/seed-data')
async def seed_data(data: SeedData, db: AsyncSession = Depends(get_db),
    admin: UserDB = Depends(admin_required)):
    try:
        departments = {}

        for item in data.departments:
            result = await db.execute(select(DepartmentDB).where(
                    DepartmentDB.name == item.name
                ))
            dept = result.scalar_one_or_none()

            if dept is None:
                dept = DepartmentDB(**item.model_dump())
                db.add(dept)
                await db.flush()

            departments[item.name] = dept.id

        students = []

        for s in data.students:
            dept_id = departments.get(s.department_name)

            if dept_id is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Department '{s.department_name}' not found"
                )

            students.append(
                StudentDB(
                    **s.model_dump(exclude={"department_name"}),
                    dept_id=dept_id
                )
            )

        db.add_all(students)
        await db.commit()

        return {"message": "Data added successfully"}

    except Exception:
        await db.rollback()
        raise