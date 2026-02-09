"""
API routes for Script management.
"""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models.script import Script
from ..schemas.script import ScriptCreate, ScriptUpdate, ScriptResponse

router = APIRouter(prefix="/api/scripts", tags=["scripts"])


@router.post("", response_model=ScriptResponse, status_code=201)
async def create_script(
    script_data: ScriptCreate,
    db: Session = Depends(get_db)
):
    """Create a new script."""
    # Check for duplicate name
    existing = db.query(Script).filter(Script.name == script_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Script with this name already exists")

    # Convert keywords to JSON string (preserve Unicode)
    keywords_json = None
    if script_data.keywords:
        keywords_json = json.dumps(script_data.keywords, ensure_ascii=False)

    script = Script(
        name=script_data.name,
        display_name=script_data.display_name,
        description=script_data.description,
        code=script_data.code,
        keywords=keywords_json,
        language=script_data.language,
        input_requirements=script_data.input_requirements,
        output_description=script_data.output_description,
        created_by=script_data.created_by,
        created_from_prompt=script_data.created_from_prompt,
    )

    db.add(script)
    db.commit()
    db.refresh(script)

    return ScriptResponse.from_orm(script)


@router.get("", response_model=List[ScriptResponse])
async def list_scripts(db: Session = Depends(get_db)):
    """List all scripts."""
    scripts = db.query(Script).order_by(Script.usage_count.desc()).all()
    return [ScriptResponse.from_orm(s) for s in scripts]


@router.get("/search", response_model=List[ScriptResponse])
async def search_scripts(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """Search scripts by name, description, or keywords."""
    search_term = f"%{q}%"

    scripts = db.query(Script).filter(
        or_(
            Script.name.ilike(search_term),
            Script.display_name.ilike(search_term),
            Script.description.ilike(search_term),
            Script.keywords.ilike(search_term),
        )
    ).order_by(Script.usage_count.desc()).all()

    return [ScriptResponse.from_orm(s) for s in scripts]


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: str,
    db: Session = Depends(get_db)
):
    """Get a script by ID."""
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    return ScriptResponse.from_orm(script)


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(
    script_id: str,
    script_data: ScriptUpdate,
    db: Session = Depends(get_db)
):
    """Update a script."""
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Update fields
    if script_data.display_name is not None:
        script.display_name = script_data.display_name
    if script_data.description is not None:
        script.description = script_data.description
    if script_data.code is not None:
        script.code = script_data.code
    if script_data.keywords is not None:
        script.keywords = json.dumps(script_data.keywords, ensure_ascii=False)
    if script_data.input_requirements is not None:
        script.input_requirements = script_data.input_requirements
    if script_data.output_description is not None:
        script.output_description = script_data.output_description

    db.commit()
    db.refresh(script)

    return ScriptResponse.from_orm(script)


@router.delete("/{script_id}", status_code=204)
async def delete_script(
    script_id: str,
    db: Session = Depends(get_db)
):
    """Delete a script."""
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    db.delete(script)
    db.commit()

    return None
