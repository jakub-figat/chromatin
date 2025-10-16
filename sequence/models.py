from sqlalchemy import String, Text, Enum, ForeignKey
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from common.models import User
from sequence.enums import SequenceType

from core.database import Base


class Sequence(Base):
    __tablename__ = "sequences"

    name: Mapped[str] = MappedColumn(String(128), nullable=False, unique=True)
    sequence_data: Mapped[str] = MappedColumn(Text, nullable=False, unique=True)
    sequence_type: Mapped[SequenceType] = MappedColumn(
        Enum(SequenceType), nullable=False
    )
    description: Mapped[str | None] = MappedColumn(Text, nullable=True)

    user_id: Mapped[int] = MappedColumn(ForeignKey("users.id"), nullable=False)
    user: Mapped[User] = relationship(User, back_populates="sequences", lazy="raise")
