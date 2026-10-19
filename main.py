from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from pwdlib import PasswordHash
from starlette.concurrency import run_in_threadpool

from database import *
from models import *
from schemas import *


password_hash = PasswordHash.recommended()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.get('/')
async def home():
    return {'message':"FastAPI async is running"}


@app.post('/students/',response_model=StudentOut)
async def create_student(data: StudentCreate, db: AsyncSession=Depends(get_db)):
    student = StudentDB(**data.model_dump())
    db.add(student)

    try:
        await db.commit()
        await db.refresh(student)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail='A Student with this email already exist'
        )
    
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

    return new_user


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

    return user

