"""
CONFIT Backend - Base Repository Implementation
================================================
SQLAlchemy-based repository implementation.
"""

from abc import ABC
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from domain.base import Entity, PaginatedResult, PaginationParams, Specification
from infrastructure.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# TYPES
# ─────────────────────────────────────────────────────────────────────────────

ModelType = TypeVar("ModelType", bound=Base)
EntityType = TypeVar("EntityType", bound=Entity)


# ─────────────────────────────────────────────────────────────────────────────
# BASE REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class BaseRepository(Generic[ModelType, EntityType], ABC):
    """Base repository implementation with common CRUD operations."""
    
    def __init__(
        self,
        session: AsyncSession,
        model_class: Type[ModelType],
        entity_class: Type[EntityType]
    ):
        self.session = session
        self.model_class = model_class
        self.entity_class = entity_class
    
    def _model_to_entity(self, model: ModelType) -> EntityType:
        """Convert ORM model to domain entity."""
        raise NotImplementedError("Subclasses must implement _model_to_entity")
    
    def _entity_to_model(self, entity: EntityType) -> ModelType:
        """Convert domain entity to ORM model."""
        raise NotImplementedError("Subclasses must implement _entity_to_model")
    
    def _update_model_from_entity(
        self,
        model: ModelType,
        entity: EntityType
    ) -> None:
        """Update model fields from entity."""
        raise NotImplementedError("Subclasses must implement _update_model_from_entity")
    
    async def get_by_id(self, id: UUID) -> Optional[EntityType]:
        """Get entity by ID."""
        query = select(self.model_class).where(self.model_class.id == str(id))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model is None:
            return None
        
        return self._model_to_entity(model)
    
    async def get_all(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[EntityType]:
        """Get all entities with optional pagination."""
        # Count query
        count_query = select(func.count()).select_from(self.model_class)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Data query
        query = select(self.model_class)
        
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.limit)
            
            if pagination.sort_by:
                sort_column = getattr(self.model_class, pagination.sort_by, None)
                if sort_column is not None:
                    if pagination.sort_order == "desc":
                        query = query.order_by(sort_column.desc())
                    else:
                        query = query.order_by(sort_column.asc())
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        entities = [self._model_to_entity(m) for m in models]
        
        total_pages = (total + (pagination.page_size if pagination else 20) - 1) // (pagination.page_size if pagination else 20)
        
        return PaginatedResult(
            items=entities,
            total=total,
            page=pagination.page if pagination else 1,
            page_size=pagination.page_size if pagination else len(entities),
            total_pages=total_pages
        )
    
    async def add(self, entity: EntityType) -> EntityType:
        """Add a new entity."""
        model = self._entity_to_model(entity)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._model_to_entity(model)
    
    async def update(self, entity: EntityType) -> EntityType:
        """Update an existing entity."""
        query = select(self.model_class).where(self.model_class.id == str(entity.id))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model is None:
            raise ValueError(f"Entity with id {entity.id} not found")
        
        self._update_model_from_entity(model, entity)
        await self.session.flush()
        await self.session.refresh(model)
        return self._model_to_entity(model)
    
    async def delete(self, id: UUID) -> bool:
        """Delete an entity by ID."""
        query = select(self.model_class).where(self.model_class.id == str(id))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model is None:
            return False
        
        await self.session.delete(model)
        await self.session.flush()
        return True
    
    async def exists(self, id: UUID) -> bool:
        """Check if entity exists."""
        query = select(func.count()).select_from(self.model_class).where(
            self.model_class.id == str(id)
        )
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0
    
    async def find(
        self,
        specification: Specification[EntityType],
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[EntityType]:
        """Find entities matching a specification."""
        # This is a simplified implementation
        # In a real implementation, you would convert the specification to SQL
        all_results = await self.get_all(pagination=None)
        matching = [e for e in all_results.items if specification.is_satisfied_by(e)]
        
        total = len(matching)
        
        if pagination:
            start = pagination.offset
            end = start + pagination.limit
            matching = matching[start:end]
        
        return PaginatedResult(
            items=matching,
            total=total,
            page=pagination.page if pagination else 1,
            page_size=pagination.page_size if pagination else len(matching),
            total_pages=(total + (pagination.page_size if pagination else 20) - 1) // (pagination.page_size if pagination else 20)
        )
    
    async def find_one(
        self,
        specification: Specification[EntityType]
    ) -> Optional[EntityType]:
        """Find a single entity matching a specification."""
        results = await self.find(specification, PaginationParams(page=1, page_size=1))
        return results.items[0] if results.items else None
    
    async def _get_by_field(
        self,
        field_name: str,
        value: Any
    ) -> Optional[EntityType]:
        """Get entity by a specific field value."""
        field = getattr(self.model_class, field_name, None)
        if field is None:
            return None
        
        query = select(self.model_class).where(field == value)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model is None:
            return None
        
        return self._model_to_entity(model)
    
    async def _get_all_by_field(
        self,
        field_name: str,
        value: Any,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[EntityType]:
        """Get all entities by a specific field value."""
        field = getattr(self.model_class, field_name, None)
        if field is None:
            return PaginatedResult(items=[], total=0, page=1, page_size=0, total_pages=0)
        
        # Count query
        count_query = select(func.count()).select_from(self.model_class).where(field == value)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Data query
        query = select(self.model_class).where(field == value)
        
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        entities = [self._model_to_entity(m) for m in models]
        
        total_pages = (total + (pagination.page_size if pagination else 20) - 1) // (pagination.page_size if pagination else 20)
        
        return PaginatedResult(
            items=entities,
            total=total,
            page=pagination.page if pagination else 1,
            page_size=pagination.page_size if pagination else len(entities),
            total_pages=total_pages
        )
