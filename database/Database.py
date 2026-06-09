import asyncio
import uuid
import bcrypt
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from database.models import Base, FileBase, UserBase
from sqlalchemy import delete, update
from pathlib import Path

db_url = "sqlite+aiosqlite:///storage.db"
engine = create_async_engine(db_url, echo=True)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


### SEND (ADD)
async def add_user_to_db(username: str, password: str):
    async with Session() as session:
        async with session.begin():
            user_uuid = str(uuid.uuid4())
            pw_hash = hash_password(password)
            new_user = UserBase(
                user_name=username,
                uuid=user_uuid,
                password_hash=pw_hash
            )
            session.add(new_user)


async def get_user_by_name(username: str):
    async with Session() as session:
        result = await session.execute(select(UserBase).where(UserBase.user_name == username))
        return result.scalars().first()


async def get_uuid_by_name(username: str) -> str | None:
    async with Session() as session:
        result = await session.execute(
            select(UserBase.uuid).where(UserBase.user_name == username)
        )
        return result.scalar_one_or_none()


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


async def add_file_to_db(username: str, file_name: str, messageid_chunk_list: list, file_size: int = 0):
    async with Session() as session:
        async with session.begin():
            img_ext = [".img", ".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif"]
            video_ext = [".mp4", ".mkv", ".mov", ".webm"]
            archive_ext = [".zip", ".rar", ".7z"]
            file_ext = Path(file_name).suffix
            if file_ext in img_ext:
                icon = "image.png"
            elif file_ext in video_ext:
                icon = "video.png"
            elif file_ext in archive_ext:
                icon = "archive.png"
            else:
                icon = "file.png"

            bd_result = await session.execute(select(UserBase).where(UserBase.user_name == username))
            user = bd_result.scalars().first()

            new_file = FileBase(
                user_uuid=user.uuid,
                file_name=file_name,
                id_chunk_list=messageid_chunk_list,
                chunk_amount=len(messageid_chunk_list),
                chunk_size=1 * 1024 * 1024,
                file_icon=icon,
                file_size=file_size,
            )
            session.add(new_file)


### GET
async def get_user_files(username: str):
    async with Session() as session:
        user_res = await session.execute(select(UserBase).where(UserBase.user_name == username))
        user = user_res.scalars().first()
        if not user:
            return []
        files_res = await session.execute(select(FileBase).where(FileBase.user_uuid == user.uuid))
        return files_res.scalars().all()


async def get_file_by_id(file_id: int):
    async with Session() as session:
        file_res = await session.execute(select(FileBase).where(FileBase.id == file_id))
        return file_res.scalars().first()


async def delete_file(file_id: int):
    async with Session() as session:
        await session.execute(delete(FileBase).where(FileBase.id == file_id))
        await session.commit()


async def rename_file(file_id: int, new_name: str):
    async with Session() as session:
        await session.execute(
            update(FileBase).where(FileBase.id == file_id).values(file_name=new_name)
        )
        await session.commit()


Session = async_sessionmaker(engine, expire_on_commit=False)


async def main():
    await create_db_and_tables()


if __name__ == "__main__":
    asyncio.run(main())