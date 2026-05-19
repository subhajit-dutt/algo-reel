from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Render(Base, TimestampMixin):
    __tablename__ = "renders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('started','succeeded','failed')",
            name="ck_renders_status",
        ),
        Index("ix_renders_scene_attempt", "scene_id", "attempt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scene_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, server_default=text("0")
    )
