from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from core.database import Base


if TYPE_CHECKING:
    from sequence.models import Sequence


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)

    sequences: Mapped["Sequence"] = relationship(
        "Sequence", back_populates="user", lazy="raise"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
