from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums import JobStatus

if TYPE_CHECKING:
    from app.db.models.scene import Scene


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "renderer IN ('manim','ai_image')",
            name="ck_jobs_renderer",
        ),
        CheckConstraint(
            "duration_target_seconds IN (30, 60, 180)",
            name="ck_jobs_duration_target",
        ),
        CheckConstraint(
            "status IN ('queued','scripting','script_ready','rendering','composing',"
            "'done','failed','cancelled','partially_failed')",
            name="ck_jobs_status",
        ),
        Index("ix_jobs_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    renderer: Mapped[str] = mapped_column(String(16), nullable=False)
    voice: Mapped[str] = mapped_column(String(64), nullable=False, default="alloy")
    duration_target_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=JobStatus.QUEUED.value)
    progress: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    script: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, server_default=text("0")
    )
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    arq_job_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    scenes: Mapped[list["Scene"]] = relationship(
        "Scene",
        back_populates="job",
        order_by="Scene.index",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
