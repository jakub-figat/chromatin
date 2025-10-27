from sqlalchemy import String, ForeignKey, UniqueConstraint
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

    @property
    def uses_file_storage(self) -> bool:
        """Returns True if sequence is stored in file, False if in database"""
        return self.file_path is not None
