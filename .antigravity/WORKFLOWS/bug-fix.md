# Workflow: Bug Fix

## Purpose
Systematic approach to identifying, fixing, and preventing bugs in Audiovault.

## When to Use
- User reports issue
- Automated tests fail
- Monitoring alerts triggered
- Code review finds problem

## Process

### 1. Reproduction

**Goal:** Consistently reproduce the bug

**Steps:**
1. Gather information:
   - User report or error logs
   - Environment (browser, OS, Docker version)
   - Steps to reproduce
   - Expected vs actual behavior
2. Create minimal reproduction:
   - Simplest steps that trigger bug
   - Note any prerequisites (auth, data state)
3. Verify in development environment
4. Check if regression (worked before)

**Output:** Clear reproduction steps

### 2. Diagnosis

**Root Cause Analysis:**

**Backend Issues:**
```bash
# Check logs
docker compose logs backend | grep ERROR

# Enable debug logging
# app/core/config.py
LOG_LEVEL = "DEBUG"

# Test API directly
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "..."}'

# Check database state
sqlite3 backend/audiovault.db
> SELECT * FROM tracks WHERE id = 123;
```

**Frontend Issues:**
```javascript
// Browser DevTools Console
// Network tab for API calls
// React DevTools for component state

// Add debug logging
console.log('State:', state);
console.log('Props:', props);

// Check error boundary
// Verify API responses
```

**Common Bug Categories:**

1. **Download Failures**
   - yt-dlp version outdated
   - Geo-restriction not handled
   - Invalid URL format
   - Network timeout

2. **Database Issues**
   - Missing migration
   - Constraint violation
   - Async session not closed
   - N+1 query problem

3. **Authentication Errors**
   - JWT expired
   - CORS misconfiguration
   - Missing auth header
   - Invalid credentials

4. **UI Bugs**
   - State not updating
   - WebSocket disconnected
   - CSS styling conflict
   - Race condition

### 3. Fix Implementation

**Example: Download Failure Bug**

**Problem:** Downloads fail for YouTube videos in certain regions

**Root Cause:** No proxy fallback for geo-restricted content

**Fix:**
```python
# app/services/download_service.py

class DownloadService:
    async def download_track(self, url: str) -> Track:
        try:
            # Primary download attempt
            return await self._download_with_ytdlp(url)
        except GeoRestrictedError:
            # Fallback to Invidious proxy
            logger.warning(f"Geo-restricted: {url}, trying proxy")
            proxy_url = await self._get_invidious_proxy(url)
            return await self._download_with_ytdlp(proxy_url)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise DownloadError(f"Failed to download: {str(e)}")
    
    async def _get_invidious_proxy(self, url: str) -> str:
        """Get Invidious proxy URL for geo-restricted content."""
        video_id = self._extract_youtube_id(url)
        return f"https://invidious.example.com/watch?v={video_id}"
```

**Example: UI State Bug**

**Problem:** Track list doesn't update after download

**Root Cause:** React Query cache not invalidated

**Fix:**
```typescript
// src/hooks/useDownload.ts

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { downloadTrack } from '@/api/downloads';

export const useDownload = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: downloadTrack,
    onSuccess: () => {
      // Invalidate tracks cache to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['tracks'] });
      queryClient.invalidateQueries({ queryKey: ['library'] });
    },
  });
};
```

### 4. Testing

**Write Regression Test:**

```python
# backend/tests/test_download_service.py

import pytest
from app.services.download_service import DownloadService, GeoRestrictedError

@pytest.mark.asyncio
async def test_geo_restricted_fallback(db_session, mocker):
    """Test that geo-restricted downloads use proxy fallback."""
    service = DownloadService(db_session)
    
    # Mock primary download to fail with geo-restriction
    mocker.patch.object(
        service,
        '_download_with_ytdlp',
        side_effect=GeoRestrictedError("Video not available")
    )
    
    # Mock proxy method
    mock_proxy = mocker.patch.object(
        service,
        '_get_invidious_proxy',
        return_value="https://invidious.example.com/watch?v=test123"
    )
    
    # Should not raise exception
    await service.download_track("https://youtube.com/watch?v=test123")
    
    # Verify proxy was used
    mock_proxy.assert_called_once()
```

**Manual Testing:**
1. Follow reproduction steps
2. Verify fix resolves issue
3. Test edge cases
4. Check for side effects
5. Test in different environments

### 5. Documentation

**Update CHANGELOG.md:**
```markdown
## [Unreleased]

### Fixed
- Geo-restricted YouTube downloads now use Invidious proxy fallback (#123)
```

**Add to Common Issues (if applicable):**
```markdown
# .antigravity/memory-bank/patterns/common-issues.md

## Geo-Restricted Downloads

**Symptom:** Download fails with "Video not available in your region"

**Cause:** YouTube regional restrictions

**Solution:** System automatically tries Invidious proxy

**Prevention:** Keep yt-dlp updated, configure multiple Invidious instances
```

### 6. Commit Message

**Format:**
```
fix: Handle geo-restricted YouTube downloads

- Add Invidious proxy fallback
- Retry downloads with proxy on geo-restriction error
- Add regression test

Fixes #123
```

### 7. Prevention

**Add Monitoring:**
```python
# app/core/monitoring.py

from prometheus_client import Counter

geo_restricted_counter = Counter(
    'downloads_geo_restricted_total',
    'Number of geo-restricted downloads'
)

# In download service
geo_restricted_counter.inc()
```

**Improve Error Messages:**
```python
raise DownloadError(
    "Download failed due to geo-restriction. "
    "Automatic proxy fallback failed. "
    "Please try again later or contact support."
)
```

**Add Documentation:**
- Update FAQ with common issue
- Add troubleshooting guide
- Document workarounds

## Bug Severity Levels

### Critical (Fix Immediately)
- Data loss or corruption
- Security vulnerability
- Service completely down
- Authentication broken

### High (Fix in 24-48h)
- Core feature broken
- Significant user impact
- Performance degradation
- Common workflow blocked

### Medium (Fix in Sprint)
- Minor feature broken
- Workaround available
- Edge case issue
- UI inconsistency

### Low (Backlog)
- Cosmetic issue
- Rare occurrence
- Documentation typo
- Nice-to-have improvement

## Checklist

- [ ] Bug reproduced consistently
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Regression test added
- [ ] Manual testing completed
- [ ] No new bugs introduced
- [ ] Documentation updated
- [ ] Changelog entry added
- [ ] Monitoring/logging improved
- [ ] Prevention measures considered
