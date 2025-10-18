from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, relationship, mapped_column

from core.database import Base
from common.models import User


if TYPE_CHECKING:
    from sequences.models import Sequence


class Project(Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(255))
    is_public: Mapped[bool] = mapped_column(default=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    user: Mapped[User] = relationship(back_populates="projects", lazy="raise")
    sequences: Mapped[list["Sequence"]] = relationship(
        back_populates="project", lazy="raise"
    )
