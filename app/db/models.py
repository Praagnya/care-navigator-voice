from datetime import datetime
from enum import Enum 
from sqlalchemy import Boolean, DateTime, Float, String, Integer, Text, func, Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class IngestionStatus(str, Enum): 
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class Provider(Base):
    __tablename__ = "providers"

    # CMS facility ID — string to preserve leading zeros (e.g. "670055")
    provider_id: Mapped[str] = mapped_column(String(10), primary_key=True)

    # Identity
    name: Mapped[str] = mapped_column(String(255), index=True)

    # Location
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Contact
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Facility attributes
    hospital_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emergency_services: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Ingestion tracking
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

class IngestionRun(Base): 
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[IngestionStatus] = mapped_column(SqlEnum(IngestionStatus), default = IngestionStatus.RUNNING, nullable=False)
    records_processed: Mapped[int] = mapped_column(Integer, default = 0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default = 0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

