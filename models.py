from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class DepartmentDB(Base):
    __tablename__ = 'departments'
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    name : Mapped[str] = mapped_column(String(100))
    place : Mapped[str] = mapped_column(String(100))

class StudentDB(Base):
    __tablename__ = 'students'
    id : Mapped[int] = mapped_column(Integer,primary_key=True)
    name : Mapped[str] = mapped_column(String(100))
    age : Mapped[int] = mapped_column(Integer)
    email : Mapped[str] = mapped_column(String(150),unique=True)
    dept_id : Mapped[int] = mapped_column(ForeignKey('departments.id'))

class UserDB(Base):
    __tablename__ = 'users'
    id : Mapped[int] = mapped_column(Integer, primary_key= True, index=True)
    username : Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email : Mapped[str] = mapped_column(String, unique=True, nullable=False, index= True)
    password : Mapped[str] = mapped_column(String, nullable=False)

    role : Mapped[int] = mapped_column(String, default="student", nullable=False)