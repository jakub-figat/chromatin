from functools import cached_property

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column

from common.models import User
from projects.models import Project
from sequences.enums import SequenceType

from core.database import Base


class Sequence(Base):
    __tablename__ = "sequences"

    name: Mapped[str] = mapped_column(String(255), unique=True)
    sequence_data: Mapped[str]

    sequence_type: Mapped[SequenceType]
    description: Mapped[str | None] = mapped_column(String(255))

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))

    user: Mapped[User] = relationship(back_populates="sequences", lazy="raise")
    project: Mapped[Project] = relationship(back_populates="sequences", lazy="raise")

    @cached_property
    def length(self) -> int:
        return len(self.sequence_data)

    @cached_property
    def gc_content(self) -> float:
        if self.sequence_type not in (SequenceType.DNA, SequenceType.RNA):
            return 0

        guanine_cytosine_count = len(
            [base for base in self.sequence_data if base in "CG"]
        )
        return guanine_cytosine_count / self.length

    @cached_property
    def molecular_weight(self) -> float:
        if self.sequence_type != SequenceType.PROTEIN:
            return 0

        # TODO for protein
        return 0
