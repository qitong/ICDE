import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .script import Script


def generate_uuid() -> str:
    return str(uuid.uuid4())


class DatasetType(enum.Enum):
    """Dataset type enumeration."""
    RAW = "RAW"          # Original uploaded data
    DERIVED = "DERIVED"  # Derived from another dataset via script


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[DatasetType] = mapped_column(
        Enum(DatasetType),
        default=DatasetType.RAW,
        nullable=False
    )

    # Version lineage (time dimension)
    parent_dataset_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True
    )

    # Derivation lineage (logic dimension)
    source_dataset_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True
    )
    script_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("scripts.id", ondelete="SET NULL"),
        nullable=True
    )

    # CRF information
    crf_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    crf_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Data structure
    patient_id_column: Mapped[Optional[str]] = mapped_column(String(100), default="SUBJID")
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    column_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Version diff (JSON string)
    diff_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    stale_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Storage
    folder_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    total_size: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    files: Mapped[List["DatasetFile"]] = relationship(
        "DatasetFile",
        back_populates="dataset",
        cascade="all, delete-orphan"
    )

    parent_dataset: Mapped[Optional["Dataset"]] = relationship(
        "Dataset",
        remote_side=[id],
        foreign_keys=[parent_dataset_id],
        backref="child_versions"
    )

    source_dataset: Mapped[Optional["Dataset"]] = relationship(
        "Dataset",
        remote_side=[id],
        foreign_keys=[source_dataset_id],
        backref="derived_datasets"
    )

    script: Mapped[Optional["Script"]] = relationship(
        "Script",
        back_populates="datasets"
    )


class DatasetFile(Base):
    __tablename__ = "dataset_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # csv, xlsx, xls
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    column_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    column_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    parse_status: Mapped[str] = mapped_column(String(20), default="pending")
    parse_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="files")


class DatasetLineage(Base):
    """Explicit lineage tracking between datasets."""
    __tablename__ = "dataset_lineage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    parent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False
    )
    child_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False
    )
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)  # VERSION_OF, DERIVED_FROM
    script_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("scripts.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
