from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.job import Job


class Scene(Base, TimestampMixin):
    __tablename__ = "scenes"
    __table_args__ = (
        UniqueConstraint("job_id", "index", name="uq_scenes_job_index"),
        CheckConstraint(
            "status IN ('pending','rendering','done','failed')",
            name="ck_scenes_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    visual_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    manim_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_prompts: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    duration_seconds: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    output_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="scenes")
