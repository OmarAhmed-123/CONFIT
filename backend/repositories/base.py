"""CONFIT Backend — Base Repository."""

from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository with common CRUD operations."""
    
    def __init__(self, db: Session, model: Type[ModelType]):
        self._db = db
        self._model = model
    
    def get_by_id(self, id: Any) -> Optional[ModelType]:
        """Get entity by ID."""
        return self._db.query(self._model).filter(self._model.id == id).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Dict[str, Any] = None,
    ) -> List[ModelType]:
        """Get all entities with pagination and optional filters."""
        query = self._db.query(self._model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self._model, key) and value is not None:
                    query = query.filter(getattr(self._model, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """Create new entity."""
        db_obj = self._model(**obj_in)
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return db_obj
    
    def update(self, id: Any, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """Update entity by ID."""
        db_obj = self.get_by_id(id)
        if not db_obj:
            return None
        
        for key, value in obj_in.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        
        self._db.commit()
        self._db.refresh(db_obj)
        return db_obj
    
    def delete(self, id: Any) -> bool:
        """Delete entity by ID."""
        db_obj = self.get_by_id(id)
        if not db_obj:
            return False
        
        self._db.delete(db_obj)
        self._db.commit()
        return True
    
    def count(self, filters: Dict[str, Any] = None) -> int:
        """Count entities with optional filters."""
        query = self._db.query(func.count(self._model.id))
        
        if filters:
            for key, value in filters.items():
                if hasattr(self._model, key) and value is not None:
                    query = query.filter(getattr(self._model, key) == value)
        
        return query.scalar() or 0
    
    def exists(self, id: Any) -> bool:
        """Check if entity exists."""
        return self.get_by_id(id) is not None
    
    def bulk_create(self, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """Bulk create entities."""
        db_objs = [self._model(**obj) for obj in objects]
        self._db.add_all(db_objs)
        self._db.commit()
        for obj in db_objs:
            self._db.refresh(obj)
        return db_objs
    
    def bulk_delete(self, ids: List[Any]) -> int:
        """Bulk delete entities by IDs."""
        count = self._db.query(self._model).filter(
            self._model.id.in_(ids)
        ).delete(synchronize_session=False)
        self._db.commit()
        return count
