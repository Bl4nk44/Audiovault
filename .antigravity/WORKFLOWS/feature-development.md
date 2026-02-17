# Workflow: Feature Development

## Purpose
Standardized process for developing new features in Audiovault.

## When to Use
- Adding new platform integration
- Creating new API endpoints
- Implementing UI components
- Extending existing functionality

## Process

### 1. Planning Phase

**Inputs:**
- Feature request from user or roadmap
- Technical requirements
- User stories

**Actions:**
1. Review memory-bank for context
2. Check similar existing implementations
3. Identify affected components:
   - Backend services/endpoints
   - Database models/migrations
   - Frontend components
   - Tests
4. Estimate complexity and breaking changes

**Outputs:**
- Implementation plan
- List of files to modify/create
- Potential risks identified

### 2. Backend Development

**For New Endpoints:**
```python
# 1. Create endpoint file
# app/api/endpoints/new_feature.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.new_feature import FeatureCreate, FeatureResponse
from app.services.new_feature_service import FeatureService

router = APIRouter()

@router.post("/", response_model=FeatureResponse, status_code=status.HTTP_201_CREATED)
async def create_feature(
    feature_data: FeatureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new feature."""
    service = FeatureService(db)
    return await service.create(feature_data, current_user.id)

# 2. Create service
# app/services/new_feature_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.new_feature import Feature
from app.schemas.new_feature import FeatureCreate

class FeatureService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: FeatureCreate, user_id: int) -> Feature:
        feature = Feature(**data.dict(), user_id=user_id)
        self.db.add(feature)
        await self.db.commit()
        await self.db.refresh(feature)
        return feature

# 3. Create models
# app/models/new_feature.py

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Feature(Base):
    __tablename__ = "features"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    user = relationship("User", back_populates="features")

# 4. Create schemas
# app/schemas/new_feature.py

from pydantic import BaseModel

class FeatureBase(BaseModel):
    name: str

class FeatureCreate(FeatureBase):
    pass

class FeatureResponse(FeatureBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

# 5. Register router
# app/api/api.py

from app.api.endpoints import new_feature

api_router.include_router(
    new_feature.router,
    prefix="/features",
    tags=["features"]
)

# 6. Create migration
# alembic revision --autogenerate -m "Add feature table"
```

**For New Platform Integration:**
```python
# app/services/extractors/new_platform.py

import re
from typing import List, Optional
from app.schemas.track import TrackExtracted

class NewPlatformExtractor:
    PLATFORM_NAME = "newplatform"
    URL_PATTERNS = [
        r"https?://(?:www\.)?newplatform\.com/track/([a-zA-Z0-9]+)",
        r"https?://(?:www\.)?newplatform\.com/playlist/([a-zA-Z0-9]+)"
    ]
    
    @classmethod
    def can_extract(cls, url: str) -> bool:
        """Check if URL is from this platform."""
        return any(re.match(pattern, url) for pattern in cls.URL_PATTERNS)
    
    @classmethod
    async def extract_tracks(cls, url: str) -> List[TrackExtracted]:
        """Extract track information from URL."""
        # Implementation depends on platform API
        tracks = []
        # ... extraction logic ...
        return tracks

# Register in app/services/download_service.py
from app.services.extractors.new_platform import NewPlatformExtractor

EXTRACTORS = [
    SpotifyExtractor,
    YouTubeExtractor,
    # ... other extractors ...
    NewPlatformExtractor,  # Add here
]
```

### 3. Frontend Development

**Component Structure:**
```typescript
// src/components/NewFeature/NewFeature.tsx

import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createFeature } from '@/api/features';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

interface NewFeatureProps {
  onSuccess?: () => void;
}

export const NewFeature: React.FC<NewFeatureProps> = ({ onSuccess }) => {
  const [name, setName] = useState('');
  const queryClient = useQueryClient();
  
  const mutation = useMutation({
    mutationFn: createFeature,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['features'] });
      onSuccess?.();
    },
  });
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({ name });
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Feature name"
      />
      <Button type="submit" loading={mutation.isPending}>
        Create Feature
      </Button>
    </form>
  );
};

// src/api/features.ts

import { apiClient } from './client';

export interface FeatureCreate {
  name: string;
}

export interface Feature extends FeatureCreate {
  id: number;
  user_id: number;
}

export const createFeature = async (data: FeatureCreate): Promise<Feature> => {
  const response = await apiClient.post('/features', data);
  return response.data;
};
```

### 4. Testing

**Backend Tests:**
```python
# backend/tests/test_new_feature.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_feature(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/features",
        json={"name": "Test Feature"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Feature"
    assert "id" in data
```

**Frontend Tests:**
```typescript
// src/components/NewFeature/NewFeature.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NewFeature } from './NewFeature';
import { createFeature } from '@/api/features';

jest.mock('@/api/features');

const queryClient = new QueryClient();

describe('NewFeature', () => {
  it('creates feature on submit', async () => {
    (createFeature as jest.Mock).mockResolvedValue({ id: 1, name: 'Test' });
    
    render(
      <QueryClientProvider client={queryClient}>
        <NewFeature />
      </QueryClientProvider>
    );
    
    fireEvent.change(screen.getByPlaceholderText('Feature name'), {
      target: { value: 'Test' }
    });
    fireEvent.click(screen.getByText('Create Feature'));
    
    await waitFor(() => {
      expect(createFeature).toHaveBeenCalledWith({ name: 'Test' });
    });
  });
});
```

### 5. Documentation

**Update Files:**
1. `README.md` - If user-facing feature
2. `CHANGELOG.md` - Add entry under "Unreleased"
3. API docs - Auto-generated by FastAPI
4. Wiki - Detailed guide if complex

### 6. Code Review Checklist

- [ ] Follows existing code patterns
- [ ] Type hints (Python) / TypeScript types
- [ ] Error handling implemented
- [ ] Tests written and passing
- [ ] No console.logs or debug code
- [ ] Database migrations created
- [ ] Environment variables documented
- [ ] Breaking changes noted
- [ ] Performance considered
- [ ] Security reviewed

### 7. Commit and PR

**Commit Message Format:**
```
feat: Add new platform integration

- Implement NewPlatformExtractor
- Add API endpoint for platform auth
- Create frontend components
- Add tests

Closes #123
```

**PR Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] All tests passing

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

## Common Pitfalls

1. **Forgetting async/await**: All DB operations must be async
2. **N+1 queries**: Use eager loading with `selectinload()`
3. **No error handling**: Always catch and handle exceptions
4. **Missing types**: TypeScript strict mode requires all types
5. **Not testing edge cases**: Empty lists, null values, etc.
6. **Hardcoded values**: Use environment variables
7. **Breaking API contracts**: Version endpoints if breaking

## Success Criteria

- [ ] Feature works as specified
- [ ] Tests cover happy path and edge cases
- [ ] Code review approved
- [ ] Documentation updated
- [ ] No regressions in existing features
- [ ] Performance acceptable
- [ ] Security considerations addressed
