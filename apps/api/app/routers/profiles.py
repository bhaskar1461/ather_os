from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel

from packages.database.connection import get_db
from packages.database.models import User, Profile as DBProfile
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/profiles", tags=["Profiles"])

class ProfileSchema(BaseModel):
    id: str
    name: str
    relation: str
    birthDate: str | None = None
    birthTime: str | None = None
    birthPlace: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    isDefault: bool

    model_config = {"from_attributes": True}

@router.get("", response_model=List[ProfileSchema])
async def get_profiles(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Get all astrology profiles associated with the logged-in user.
    """
    db_profiles = db.query(DBProfile).filter(DBProfile.user_id == user.id).all()
    
    # Map database underscore names to Pydantic camelCase schema
    response = []
    for p in db_profiles:
        response.append(
            ProfileSchema(
                id=p.id,
                name=p.name,
                relation=p.relation,
                birthDate=p.birth_date,
                birthTime=p.birth_time,
                birthPlace=p.birth_place,
                latitude=p.latitude,
                longitude=p.longitude,
                timezone=p.timezone,
                isDefault=p.is_default
            )
        )
    return response

@router.post("", response_model=ProfileSchema)
async def create_or_update_profile(
    profile: ProfileSchema,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Create or update an astrology profile.
    """
    db_profile = db.query(DBProfile).filter(DBProfile.id == profile.id, DBProfile.user_id == user.id).first()
    
    if db_profile:
        # Update existing profile
        db_profile.name = profile.name
        db_profile.relation = profile.relation
        db_profile.birth_date = profile.birthDate
        db_profile.birth_time = profile.birthTime
        db_profile.birth_place = profile.birthPlace
        db_profile.latitude = profile.latitude
        db_profile.longitude = profile.longitude
        db_profile.timezone = profile.timezone
        db_profile.is_default = profile.isDefault
    else:
        # Create new profile
        db_profile = DBProfile(
            id=profile.id,
            user_id=user.id,
            name=profile.name,
            relation=profile.relation,
            birth_date=profile.birthDate,
            birth_time=profile.birthTime,
            birth_place=profile.birthPlace,
            latitude=profile.latitude,
            longitude=profile.longitude,
            timezone=profile.timezone,
            is_default=profile.isDefault
        )
        db.add(db_profile)
        
    db.commit()
    db.refresh(db_profile)
    
    return ProfileSchema(
        id=db_profile.id,
        name=db_profile.name,
        relation=db_profile.relation,
        birthDate=db_profile.birth_date,
        birthTime=db_profile.birth_time,
        birthPlace=db_profile.birth_place,
        latitude=db_profile.latitude,
        longitude=db_profile.longitude,
        timezone=db_profile.timezone,
        isDefault=db_profile.is_default
    )

@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Delete a specific astrology profile.
    """
    db_profile = db.query(DBProfile).filter(DBProfile.id == profile_id, DBProfile.user_id == user.id).first()
    if not db_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    db.delete(db_profile)
    db.commit()
    return {"status": "success"}
