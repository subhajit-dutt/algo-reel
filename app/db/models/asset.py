from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("job_id", "scene_id", "kind", name="uq_assets_job_scene_kind"),
        CheckConstraint(
            "kind IN ('audio','scene_mp4','final_mp4','image','manim_log')",
            name="ck_assets_kind",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    scene_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
