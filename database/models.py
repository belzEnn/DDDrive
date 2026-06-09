from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, func, JSON
from datetime import datetime


class Base(DeclarativeBase):
    pass


class FileBase(Base):
    __tablename__ = "storage"

    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    user_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    file_name: Mapped[str] = mapped_column(nullable=False)
    id_chunk_list: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    chunk_amount: Mapped[int] = mapped_column(nullable=False)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    chunk_size: Mapped[int] = mapped_column(nullable=False)
    file_icon: Mapped[str] = mapped_column(nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False, default=0)  # размер в байтах


class UserBase(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_name: Mapped[str] = mapped_column(nullable=False, unique=True)
    uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)