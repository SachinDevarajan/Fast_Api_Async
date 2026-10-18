from pydantic import BaseModel, ConfigDict, Field, EmailStr


class StudentCreate(BaseModel):
    name : str = Field(min_length=1,max_length=100)
    age : int = Field(gt=0)
    email :EmailStr


class StudentUpdate(BaseModel):
    name : str = Field(min_length=1, max_length=100)
    age : int = Field(gt=0)
    email : EmailStr


class StudentOut(BaseModel):
    id : int
    name : str
    age : int
    email : EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username : str = Field(min_length=3, max_length=50)
    email : EmailStr
    password : str = Field(min_length=8,max_length=128)


class UserOut(BaseModel):
    id : int
    username : str
    email : EmailStr
    role : str


class UserLogin(BaseModel):
    email : EmailStr
    password : str = Field(min_length=8,max_length=128)