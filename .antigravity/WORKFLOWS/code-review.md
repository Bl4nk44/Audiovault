# Workflow: Code Review

## Purpose
Ensure code quality, maintainability, and consistency across Audiovault codebase.

## When to Use
- Before merging any pull request
- When assisting with code improvements
- During pair programming sessions

## Review Checklist

### 1. Code Quality

#### Python/Backend
```python
# ✅ Good
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

async def get_track(
    db: AsyncSession,
    track_id: int
) -> Optional[Track]:
    """Retrieve track by ID.
    
    Args:
        db: Database session
        track_id: Unique track identifier
    
    Returns:
        Track object or None if not found
    """
    result = await db.execute(
        select(Track).where(Track.id == track_id)
    )
    return result.scalar_one_or_none()

# ❌ Bad
def get_track(db, id):
    # No type hints, no docstring, blocking call
    return db.query(Track).filter(Track.id == id).first()
```

#### TypeScript/Frontend
```typescript
// ✅ Good
interface TrackListProps {
  tracks: Track[];
  onSelect: (track: Track) => void;
  loading?: boolean;
}

export const TrackList: React.FC<TrackListProps> = ({
  tracks,
  onSelect,
  loading = false
}) => {
  if (loading) return <Spinner />;
  
  return (
    <div className="space-y-2">
      {tracks.map(track => (
        <TrackItem
          key={track.id}
          track={track}
          onClick={() => onSelect(track)}
        />
      ))}
    </div>
  );
};

// ❌ Bad
export const TrackList = (props: any) => {
  // Any type, inconsistent naming, no error handling
  return (
    <div>
      {props.data.map(t => <div onClick={props.cb}>{t.name}</div>)}
    </div>
  );
};
```

### 2. Architecture & Design

**Check for:**
- [ ] Single Responsibility Principle followed
- [ ] DRY (Don't Repeat Yourself) principle
- [ ] Proper separation of concerns
- [ ] Consistent with existing patterns
- [ ] No circular dependencies
- [ ] Appropriate abstraction level

**Example Issues:**

❌ **Mixing concerns:**
```python
# Endpoint doing too much
@router.post("/download")
async def download(url: str, db: AsyncSession):
    # Validation logic
    if not url.startswith("http"):
        raise ValueError
    
    # Business logic
    track_info = extract_metadata(url)
    file_path = download_file(url)
    
    # Database logic
    track = Track(**track_info, path=file_path)
    db.add(track)
    await db.commit()
    
    return track
```

✅ **Proper separation:**
```python
# Endpoint
@router.post("/download", response_model=TrackResponse)
async def download(
    data: DownloadRequest,
    service: DownloadService = Depends(get_download_service)
):
    return await service.download_track(data.url)

# Service
class DownloadService:
    async def download_track(self, url: str) -> Track:
        # Orchestrates the flow
        validator.validate_url(url)
        metadata = await extractor.extract(url)
        file_path = await downloader.download(url)
        return await repository.create_track(metadata, file_path)
```

### 3. Error Handling

**Requirements:**
- [ ] All error cases handled
- [ ] Specific exceptions used
- [ ] Proper HTTP status codes
- [ ] User-friendly error messages
- [ ] Errors logged appropriately

```python
# ✅ Good error handling
from app.core.exceptions import TrackNotFoundError, DownloadError

@router.get("/tracks/{track_id}")
async def get_track(
    track_id: int,
    service: TrackService = Depends()
):
    try:
        track = await service.get_track(track_id)
        if not track:
            raise TrackNotFoundError(f"Track {track_id} not found")
        return track
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve track"
        )

# ❌ Bad error handling
@router.get("/tracks/{track_id}")
async def get_track(track_id: int):
    track = await get_track_from_db(track_id)  # Can raise multiple exceptions
    return track  # No error handling, no validation
```

### 4. Performance

**Check for:**
- [ ] No N+1 query problems
- [ ] Appropriate use of indexes
- [ ] Efficient algorithms (Big O)
- [ ] Lazy loading where appropriate
- [ ] Caching considered
- [ ] No blocking operations in async code

```python
# ❌ N+1 Problem
tracks = await db.execute(select(Track))
for track in tracks.scalars():
    # Separate query for each track!
    playlist = await db.get(Playlist, track.playlist_id)

# ✅ Eager Loading
tracks = await db.execute(
    select(Track).options(selectinload(Track.playlist))
)
for track in tracks.scalars():
    # Playlist already loaded
    playlist = track.playlist
```

### 5. Security

**Check for:**
- [ ] No SQL injection vulnerabilities
- [ ] Input validation with Pydantic
- [ ] Authentication/authorization enforced
- [ ] Secrets in environment variables
- [ ] No sensitive data in logs
- [ ] CORS properly configured
- [ ] Rate limiting on public endpoints

```python
# ✅ Secure
from app.core.security import get_current_user

@router.delete("/tracks/{track_id}")
async def delete_track(
    track_id: int,
    current_user: User = Depends(get_current_user),  # Auth required
    db: AsyncSession = Depends(get_db)
):
    track = await db.get(Track, track_id)
    if track.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.delete(track)
    await db.commit()

# ❌ Insecure
@router.delete("/tracks/{track_id}")
async def delete_track(track_id: int, db: AsyncSession):
    # No authentication check!
    track = await db.get(Track, track_id)
    await db.delete(track)
```

### 6. Testing

**Requirements:**
- [ ] Unit tests for business logic
- [ ] Integration tests for API endpoints
- [ ] Edge cases covered
- [ ] Happy path and sad path tested
- [ ] Mocks used appropriately
- [ ] Test names are descriptive

```python
# ✅ Good test
@pytest.mark.asyncio
async def test_download_track_with_geo_restriction(
    db_session,
    mock_ytdlp
):
    """Test download fallback when video is geo-restricted."""
    service = DownloadService(db_session)
    
    # Setup
    mock_ytdlp.side_effect = [
        GeoRestrictedError("Not available"),  # First attempt fails
        {"title": "Test Track", "artist": "Test"}  # Proxy succeeds
    ]
    
    # Execute
    track = await service.download_track("https://youtube.com/watch?v=test")
    
    # Assert
    assert track.title == "Test Track"
    assert mock_ytdlp.call_count == 2  # Tried twice

# ❌ Bad test
async def test_download():
    # Vague name, no setup, no assertions
    result = await download_track("some_url")
```

### 7. Documentation

**Check for:**
- [ ] Docstrings for public functions/classes
- [ ] Complex logic explained with comments
- [ ] README updated if needed
- [ ] API changes documented
- [ ] CHANGELOG entry added

```python
# ✅ Well documented
class DownloadService:
    """Service for downloading tracks from various platforms.
    
    Handles multi-platform extraction, fallback logic, and metadata
    tagging. Uses yt-dlp as the primary download engine.
    
    Attributes:
        db: Database session for persisting tracks
        extractors: List of platform-specific extractors
    """
    
    async def download_track(self, url: str) -> Track:
        """Download track from URL with automatic fallback.
        
        Attempts primary download, then tries:
        1. Alternative search queries
        2. Cross-platform sources
        3. Proxy services for geo-restrictions
        
        Args:
            url: Valid URL from supported platform
        
        Returns:
            Track object with file path and metadata
        
        Raises:
            DownloadError: If all download attempts fail
            ValidationError: If URL format is invalid
        """
        # Implementation
```

### 8. Style & Consistency

**Python:**
- [ ] Black formatter applied
- [ ] isort for imports
- [ ] Type hints present
- [ ] PEP 8 compliant
- [ ] snake_case naming

**TypeScript:**
- [ ] Prettier formatted
- [ ] ESLint rules followed
- [ ] camelCase naming
- [ ] Interfaces/types defined

### 9. Audiovault-Specific

**Backend:**
- [ ] All DB operations are async
- [ ] WebSocket updates for long operations
- [ ] Proper error handling with custom exceptions
- [ ] Services use dependency injection
- [ ] Migrations created for schema changes

**Frontend:**
- [ ] React Query for server state
- [ ] TailwindCSS for styling (no inline styles)
- [ ] Framer Motion for animations
- [ ] Proper TypeScript types (no `any`)
- [ ] Components are memoized if expensive

## Review Process

### 1. Initial Scan
- Read PR description
- Check files changed
- Identify scope and impact
- Note any red flags

### 2. Detailed Review
- Review each file systematically
- Check against checklist
- Test locally if needed
- Verify tests pass

### 3. Provide Feedback

**Good Feedback:**
```markdown
## Architecture
✅ Good separation of concerns in the service layer

💡 Consider: Could we extract the retry logic into a reusable decorator?

## Performance
❌ N+1 query in `get_playlists_with_tracks()` (line 45)
Suggestion: Use `selectinload(Playlist.tracks)` for eager loading

## Security
⚠️ Missing rate limit on upload endpoint
```

**Bad Feedback:**
```markdown
"This code is bad"
"Why did you do it this way?"
"Rewrite everything"
```

### 4. Approve or Request Changes

**Approve if:**
- All critical issues resolved
- Minor issues documented (can be follow-up)
- Tests passing
- Meets quality standards

**Request Changes if:**
- Critical bugs present
- Security vulnerabilities
- Breaking changes without migration
- Tests failing
- Major architectural concerns

## Quick Reference

### Must-Have Before Approval
1. ✅ Tests passing (CI green)
2. ✅ No console.logs or debug code
3. ✅ Type hints/types present
4. ✅ Error handling implemented
5. ✅ Documentation updated
6. ✅ No obvious security issues
7. ✅ Follows existing patterns
8. ✅ CHANGELOG updated
