import asyncio

from database import SessionLocal
from models import UserDB
from sqlalchemy import select


async def make_admin():
    async with SessionLocal() as db:
        email = "sachin@gmail.com"

        result = await db.execute(
            select(UserDB).where(UserDB.email == email)
        )

        user = result.scalar_one_or_none()

        if user is None:
            print("User not found. Register first.")
        else:
            user.role = "admin"
            await db.commit()
            print("Admin role assigned successfully.")


asyncio.run(make_admin())
