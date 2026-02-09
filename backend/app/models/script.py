import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .dataset import Dataset


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Script(Base):
    """Script model for storing reusable data transformation scripts."""
    __tablename__ = "scripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Identification
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Description for LLM matching
    description: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Code
    language: Mapped[str] = mapped_column(String(20), default="python")
    code: Mapped[str] = mapped_column(Text, nullable=False)

    # Input/Output specification
    input_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    output_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Origin
    created_by: Mapped[str] = mapped_column(String(50), default="user")  # user | llm
    created_from_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Usage statistics
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_script_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("scripts.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    datasets: Mapped[List["Dataset"]] = relationship(
        "Dataset",
        back_populates="script"
    )

    parent_script: Mapped[Optional["Script"]] = relationship(
        "Script",
        remote_side=[id],
        backref="child_scripts"
    )
