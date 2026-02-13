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

    # Input/Output specification (legacy, kept for backward compatibility)
    input_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured metadata for LLM tool calling
    # parameters_schema: JSON Schema for input parameters (OpenAI function calling format)
    # {
    #   "type": "object",
    #   "properties": {
    #     "adsl_df": {"type": "DataFrame", "description": "Subject-level dataset"},
    #     "population": {"type": "string", "enum": ["all", "safety", "itt"]}
    #   },
    #   "required": ["adsl_df"]
    # }
    parameters_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # returns_schema: JSON Schema for return value
    # {"type": "DataFrame", "description": "Summary statistics table"}
    returns_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # functions: JSON array of functions/methods provided by this script
    # [{"name": "count_patients", "description": "Count unique patients", "is_main": true}]
    functions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # use_cases: JSON array of example use cases for LLM to understand when to use this script
    # ["Count total patients in study", "Get patient distribution by treatment arm"]
    use_cases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # example_calls: JSON array of example function calls
    # [{"input": "count_patients(adsl_df)", "output": "{'total': 100, 'by_arm': {...}}"}]
    example_calls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

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
