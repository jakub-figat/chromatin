from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship, mapped_column

from common.models import User
from projects.models import Project
from sequences.enums import SequenceType

from core.database import Base


class Sequence(Base):
    __tablename__ = "sequences"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_sequence_name"),
    )

    name: Mapped[str] = mapped_column(String(255))

    # Hybrid storage: small sequences in DB, large sequences in files
    sequence_data: Mapped[str | None] = mapped_column(String(10000))  # Max 10KB in DB
    file_path: Mapped[str | None] = mapped_column(
        String(500)
    )  # Path/key for file storage

    # Pre-calculated properties (always stored for performance)
    length: Mapped[int]
    gc_content: Mapped[float | None]
    molecular_weight: Mapped[float | None]

    sequence_type: Mapped[SequenceType]
    description: Mapped[str | None] = mapped_column(String(255))

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))

    user: Mapped[User] = relationship(back_populates="sequences", lazy="raise")
    project: Mapped[Project] = relationship(back_populates="sequences", lazy="raise")
    structure: Mapped["SequenceStructure | None"] = relationship(
        back_populates="sequence", lazy="raise", cascade="all, delete-orphan"
    )

    @property
    def uses_file_storage(self) -> bool:
        """Returns True if sequence is stored in file, False if in database"""
        return self.file_path is not None


class SequenceStructure(Base):
    __tablename__ = "sequence_structures"

    sequence_id: Mapped[int] = mapped_column(
        ForeignKey("sequences.id", ondelete="CASCADE"), unique=True
    )
    file_path: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(50))
    sequence_hash: Mapped[str] = mapped_column(String(64))

    residue_count: Mapped[int]
    mean_confidence: Mapped[float]
    min_confidence: Mapped[float]
    max_confidence: Mapped[float]
    confidence_scores: Mapped[list[float]] = mapped_column(JSONB)

    sequence: Mapped[Sequence] = relationship(back_populates="structure", lazy="raise")
