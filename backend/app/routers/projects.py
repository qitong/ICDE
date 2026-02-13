import uuid
from collections import defaultdict
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.project import Project
from ..models.dataset import Dataset
from ..schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectTree,
    Study,
    StudyVersion,
    DatasetSummary,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
):
    """Create a new project."""
    project = Project(
        id=str(uuid.uuid4()),
        name=project_in.name,
        description=project_in.description,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """List all projects."""
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get project details."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
):
    """Update a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_in.name is not None:
        project.name = project_in.name
    if project_in.description is not None:
        project.description = project_in.description

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project and all its datasets."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    return None


@router.get("/{project_id}/tree", response_model=ProjectTree)
async def get_project_tree(project_id: str, db: Session = Depends(get_db)):
    """Get hierarchical tree structure of a project (Study > Version > Datasets)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all datasets for this project
    datasets = (
        db.query(Dataset)
        .filter(Dataset.project_id == project_id)
        .order_by(Dataset.study_name, Dataset.version_name, Dataset.name)
        .all()
    )

    # Build hierarchical structure
    # study_name -> version_name -> list of datasets
    study_map = defaultdict(lambda: defaultdict(list))

    for dataset in datasets:
        study_name = dataset.study_name or "Uncategorized"
        version_name = dataset.version_name or "Default"

        dataset_summary = DatasetSummary(
            id=dataset.id,
            name=dataset.name,
            type=dataset.type.value if dataset.type else "RAW",
            file_count=dataset.file_count,
            created_at=dataset.created_at,
        )
        study_map[study_name][version_name].append(dataset_summary)

    # Convert to Study/StudyVersion structure
    studies = []
    for study_name in sorted(study_map.keys()):
        versions = []
        for version_name in sorted(study_map[study_name].keys()):
            versions.append(
                StudyVersion(
                    name=version_name,
                    datasets=study_map[study_name][version_name],
                )
            )
        studies.append(Study(name=study_name, versions=versions))

    return ProjectTree(
        project_id=project.id,
        project_name=project.name,
        studies=studies,
    )
