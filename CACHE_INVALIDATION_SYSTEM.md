# Cache Invalidation & Real-Time UI Update System

## Overview

This document explains the comprehensive cache invalidation system that ensures the UI **always** reflects database changes without fail, particularly for:
- Brand consolidations (duplicates, SKU merges, URL-based company matches)
- Website enrichment updates
- Apollo contact additions
- Any database modifications

---

## Problem Solved

**Before**: The UI could show stale data for up to 10 minutes after database changes because:
- Filter cache: 10-minute TTL
- Brand list cache: 2-minute TTL
- All brands cache: 5-minute TTL
- Stats cache: 3-minute TTL
- **No cache invalidation on database modifications**

**After**: UI updates **immediately** (within 5 seconds) when data changes through:
1. Automatic cache invalidation on all database writes
2. Database version tracking
3. Client-side polling with auto-refresh
4. Visual notifications to users

---

## System Architecture

### 1. Server-Side Components

#### A. Database Version Tracking (`app.py:60-63`)
```python
db_version = {
    'version': int(time.time() * 1000),  # Millisecond timestamp
    'last_modified': datetime.now().isoformat()
}
```
- Global version number incremented on every database change
- Millisecond precision ensures uniqueness
- Tracked timestamp for debugging

#### B. Enhanced Cache System (`app.py:65-85`)
```python
filter_cache = {
    'counts': None,
    'timestamp': 0,
    'db_version': 0  # NEW: Tracks which DB version this cache is valid for
}
```
- Each cache now includes `db_version` field
- Cache is invalidated if version mismatch **OR** TTL expired

#### C. Comprehensive Cache Invalidation (`app.py:87-104`)
```python
def invalidate_all_caches():
    """
    Invalidate all caches when database is modified
    This ensures UI always shows fresh data after consolidations, merges, updates
    """
    global filter_cache, brand_list_cache, all_brands_cache, stats_cache, db_version

    # Update database version to invalidate all caches
    db_version['version'] = int(time.time() * 1000)
    db_version['last_modified'] = datetime.now().isoformat()

    # Clear all cache data
    filter_cache = {'counts': None, 'timestamp': 0, 'db_version': 0}
    brand_list_cache = {'data': None, 'timestamp': 0, 'query_hash': None, 'db_version': 0}
    all_brands_cache = {'data': None, 'timestamp': 0, 'db_version': 0}
    stats_cache = {'data': None, 'timestamp': 0, 'db_version': 0}

    logger.info(f"🔄 All caches invalidated - DB version: {db_version['version']}")
```

**Called automatically after**:
- `brand_db.consolidate_brands()` - Brand consolidations
- `brand_db.update_brand_enrichment()` - Website updates
- `brand_db.update_brand_apollo_data()` - Apollo contact additions
- `brand_db.update_importers_list()` - Importer data changes
- All other database write operations (11 locations in app.py)

#### D. Version-Aware Cache Getters (`app.py:106-167`)
```python
def get_cached_all_brands():
    global all_brands_cache, db_version
    current_time = time.time()

    # Check if cache is valid (both time-based AND version-based)
    cache_valid = (
        all_brands_cache['data'] and
        (current_time - all_brands_cache['timestamp']) < ALL_BRANDS_CACHE_TTL and
        all_brands_cache['db_version'] == db_version['version']  # NEW
    )

    if cache_valid:
        return all_brands_cache['data']

    # Cache miss - reload from database
    all_brands_cache['data'] = brand_db.get_all_brands()
    all_brands_cache['timestamp'] = current_time
    all_brands_cache['db_version'] = db_version['version']  # NEW
    return all_brands_cache['data']
```

---

### 2. API Endpoints

#### A. Database Version Endpoint (`/api/database_version`)
```bash
curl http://localhost:5000/api/database_version
```

**Response:**
```json
{
  "version": 1762358119842,
  "last_modified": "2025-11-05T15:55:19.842714",
  "success": true
}
```

**Headers:**
```
Cache-Control: no-cache, no-store, must-revalidate
Pragma: no-cache
Expires: 0
```

**Purpose**: Client-side polling to detect database changes

---

#### B. Cache Status Endpoint (`/api/cache_status`)
```bash
curl http://localhost:5000/api/cache_status
```

**Response:**
```json
{
  "db_version": {
    "version": 1762358119842,
    "last_modified": "2025-11-05T15:55:19.842714"
  },
  "caches": {
    "filter": {
      "cached": true,
      "timestamp": 1762358100,
      "db_version": 1762358119842,
      "age_seconds": 19
    },
    "all_brands": {
      "cached": true,
      "count": 38596,
      "timestamp": 1762358095,
      "db_version": 1762358119842,
      "age_seconds": 24
    }
    // ... other caches
  }
}
```

**Purpose**: Debugging cache state and version synchronization

---

### 3. Client-Side Components

#### A. Cache Buster Script (`web/static/js/cache_buster.js`)

**Features**:
- Polls `/api/database_version` every 5 seconds
- Compares current version with stored version
- Detects database changes instantly
- Shows visual notification to user
- Auto-refreshes page after 2 seconds

**Configuration Options**:
```javascript
// In your HTML page, set these BEFORE including cache_buster.js:
window.CACHE_BUSTER_POLL_INTERVAL = 3000;  // Poll every 3 seconds (default: 5000)
window.CACHE_BUSTER_AUTO_REFRESH = true;   // Auto-refresh on change (default: true)
window.CACHE_BUSTER_NOTIFICATIONS = true;  // Show notifications (default: true)
window.CACHE_BUSTER_DEBUG = true;          // Enable console logging (default: false)
window.DISABLE_CACHE_BUSTER = false;       // Disable entirely (default: false)
```

**User Experience**:
1. User is on `/brands` page
2. Someone else (or another tab) consolidates a brand
3. Within 5 seconds:
   - Cache Buster detects version change
   - Purple notification appears: "🔄 Data Updated"
   - Page auto-refreshes after 2 seconds
   - User sees updated brand list

**Visual Notification**:
```
┌──────────────────────────────────────┐
│ 🔄  Data Updated                     │
│     Database modified at 3:55:19 PM  │
│     • Refreshing...                  │
└──────────────────────────────────────┘
```

#### B. Pages with Cache Buster Enabled
- ✅ `/brands` - Brand registry
- ✅ `/audit` - Consolidation review
- ✅ `/brand/<name>` - Individual brand detail
- 🔄 Can be added to any page (see "How to Enable" below)

---

## How It Works: Step-by-Step

### Scenario: Brand Consolidation

**Step 1**: User approves consolidation on `/audit` page
```
POST /consolidation/approve_proposal
{
  "proposal_id": "sku_to_brand_example_com_2_brands",
  "force_approval": true
}
```

**Step 2**: Server executes consolidation (`app.py:2808`)
```python
result = brand_db.consolidate_brands(canonical_name, brands_to_merge)
```

**Step 3**: Server invalidates caches (`app.py:2846`)
```python
invalidate_filter_cache()  # → calls invalidate_all_caches()
```

**Step 4**: Database version updated
```
Before: version = 1762358000000
After:  version = 1762358119842  (current timestamp)
```

**Step 5**: Client detects change (within 5 seconds)
```javascript
// cache_buster.js polls every 5 seconds
const response = await fetch('/api/database_version');
const data = await response.json();

if (data.version !== this.currentVersion) {
    // Version changed!
    this.handleVersionChange(data);
}
```

**Step 6**: User notified & page refreshed
```javascript
showUpdateNotification();  // Purple notification
setTimeout(() => window.location.reload(), 2000);  // Refresh after 2s
```

**Step 7**: Fresh data loaded
- All caches have `db_version = 0` (invalidated)
- New version is `1762358119842`
- Cache getters see mismatch → reload from database
- UI shows consolidated brands

---

## Verification & Testing

### 1. Check System Status
```bash
# Verify cache invalidation system is loaded
curl http://localhost:5000/api/cache_status

# Get current database version
curl http://localhost:5000/api/database_version

# Check database stats
curl http://localhost:5000/get_database_stats
```

### 2. Test Cache Invalidation Manually

**Terminal 1** - Monitor cache status:
```bash
watch -n 1 'curl -s http://localhost:5000/api/cache_status | jq .db_version'
```

**Terminal 2** - Simulate database change:
```bash
# Make any database modification (e.g., approve consolidation via UI)
# OR trigger via API
curl -X POST http://localhost:5000/consolidation/approve_proposal \
  -H "Content-Type: application/json" \
  -d '{"proposal_id": "some_proposal", "force_approval": true}'
```

**Expected Result**: Version number in Terminal 1 updates immediately

### 3. Test Client-Side Auto-Refresh

**Browser Console**:
```javascript
// Enable debug mode
window.CACHE_BUSTER_DEBUG = true;

// Check current version
console.log('Current version:', window.cacheBuster.currentVersion);

// Force refresh manually
window.refreshData();
```

**Expected Console Output**:
```
🔄 Cache Buster initialized with version: 1762358119842
🔄 Polling started (every 5s)
🔄 Database version changed: {old: 1762358119842, new: 1762358120000, ...}
🔄 Auto-refreshing page due to database changes
```

### 4. Verify Consolidation Updates UI

**Test Flow**:
1. Open `/brands` in Browser A
2. Open `/audit` in Browser B
3. In Browser B: Approve a consolidation
4. Watch Browser A:
   - ✅ Notification appears within 5 seconds
   - ✅ Page auto-refreshes
   - ✅ Consolidated brand is gone
   - ✅ Canonical brand shows updated SKU count

---

## How to Enable on New Pages

### Option 1: Add to Existing Page Template

Add before `</body>` tag:
```html
<!-- Cache Buster for Real-time UI Updates -->
<script src="{{ url_for('static', filename='js/cache_buster.js') }}"></script>
```

### Option 2: Customize Behavior

```html
<script>
    // Configure before loading cache_buster.js
    window.CACHE_BUSTER_POLL_INTERVAL = 3000;  // 3 seconds
    window.CACHE_BUSTER_DEBUG = true;          // Enable logging
</script>
<script src="{{ url_for('static', filename='js/cache_buster.js') }}"></script>
```

### Option 3: Disable for Specific Page

```html
<script>
    window.DISABLE_CACHE_BUSTER = true;  // Don't load cache buster
</script>
<script src="{{ url_for('static', filename='js/cache_buster.js') }}"></script>
```

---

## Performance Considerations

### Cache Benefits
- **Reduced Database Load**: Caches prevent repeated expensive queries
- **Fast Page Loads**: Cached data served in microseconds vs 100ms+ DB queries
- **TTL Fallback**: Even if versioning fails, TTL ensures eventual freshness

### Polling Overhead
- **Network**: 1 tiny HTTP request per 5 seconds per browser tab
- **Server**: Negligible (version endpoint is a simple JSON response)
- **Battery**: Minimal (pauses when tab is hidden)

### Production Optimizations
```javascript
// Recommended production settings:
window.CACHE_BUSTER_POLL_INTERVAL = 10000;  // 10 seconds (reduce from 5s)
window.CACHE_BUSTER_AUTO_REFRESH = true;    // Keep auto-refresh
window.CACHE_BUSTER_NOTIFICATIONS = true;   // Keep notifications
window.CACHE_BUSTER_DEBUG = false;          // Disable debug logging
```

---

## Troubleshooting

### Issue: UI Not Updating After Consolidation

**Check 1**: Verify cache invalidation is called
```bash
# Check server logs for:
"🔄 All caches invalidated - DB version: ..."
```

**Check 2**: Verify database version is incrementing
```bash
# Before consolidation
curl http://localhost:5000/api/database_version

# After consolidation
curl http://localhost:5000/api/database_version

# Version should be different
```

**Check 3**: Verify cache_buster.js is loaded
```javascript
// Browser console:
window.cacheBuster
// Should return CacheBuster instance, not undefined
```

### Issue: Notification Not Appearing

**Check 1**: Verify cache buster is running
```javascript
// Browser console:
window.cacheBuster.isPolling
// Should return true
```

**Check 2**: Enable debug mode
```javascript
// Browser console:
window.CACHE_BUSTER_DEBUG = true;
window.cacheBuster.getCurrentVersion();
// Should log version check
```

**Check 3**: Check browser console for errors
```javascript
// Look for:
// - Failed to fetch errors
// - CORS errors
// - JavaScript errors
```

### Issue: Page Refreshing Too Often

**Cause**: Database version incrementing too frequently

**Solution**: Check what's triggering `invalidate_all_caches()`
```bash
# Server logs show every cache invalidation
grep "All caches invalidated" logs/flask.log
```

---

## Advanced Features

### Manual Refresh Button

Add to any page:
```html
<button onclick="window.refreshData()">
    🔄 Refresh Data
</button>
```

### Custom Notification Styling

Override in your page CSS:
```css
#cache-buster-notification {
    /* Custom styling */
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
}
```

### Conditional Auto-Refresh

```javascript
// Only auto-refresh if user hasn't typed in last 30 seconds
let lastUserActivity = Date.now();

document.addEventListener('keydown', () => {
    lastUserActivity = Date.now();
});

window.cacheBuster.autoRefresh = function() {
    const timeSinceActivity = Date.now() - lastUserActivity;
    if (timeSinceActivity > 30000) {  // 30 seconds
        window.location.reload();
    } else {
        console.log('User active - delaying refresh');
        setTimeout(() => this.autoRefresh(), 5000);
    }
};
```

---

## Summary

This system **guarantees** UI freshness through:

1. **Server-Side Version Tracking**: Every database change increments version
2. **Dual-Layer Cache Validation**: Time-based TTL + version-based invalidation
3. **Automatic Cache Invalidation**: Called after all 11 database write operations
4. **Client-Side Polling**: Detects changes within 5 seconds
5. **User-Friendly Notifications**: Visual feedback before auto-refresh
6. **Smart Page Refresh**: Auto-refresh with configurable delay

**Result**: UI **ALWAYS** reflects database state, typically within 5 seconds of any change, with zero manual intervention required.

---

*Last Updated: November 5, 2025*
*System Version: v2.0 - Comprehensive Cache Invalidation*
