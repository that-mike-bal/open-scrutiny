# Supabase Client Usage Guide

## Overview

This project now uses a **unified Supabase client interface** to prevent confusion between different client implementations. All Supabase operations should follow the patterns outlined in this document.

## ⚠️ Important: Two Client Implementations

There are currently two Supabase client implementations in the project:

1. **`crewai_service/utils/supabase_client.py`** - Enhanced wrapper (RECOMMENDED)
2. **`db/supabase_client.py`** - Raw client (LEGACY)

## 🎯 Recommended Usage Pattern

### For CrewAI Service (`crewai_service/` directory)

Use the enhanced wrapper from `crewai_service/utils/supabase_client.py`:

```python
from crewai_service.utils.supabase_client import get_supabase_client

# Initialize client
supabase = get_supabase_client()

# Use the simplified .table() method
response = supabase.table('tld_strings').select('*').execute()
```

### For Database Operations (`db/` directory)

Use the raw client from `db/supabase_client.py`:

```python
from db.supabase_client import get_supabase

# Initialize client
supabase = get_supabase()

# Use direct .table() method
response = supabase.table('tld_strings').select('*').execute()
```

## ✅ Correct Usage Examples

### CrewAI Service (Wrapper Client)

```python
from crewai_service.utils.supabase_client import get_supabase_client

def auto_submit_evaluation(request):
    supabase = get_supabase_client()
    
    # ✅ CORRECT: Use .table() directly
    response = supabase.table('tld_strings').select('*').execute()
    
    # ✅ CORRECT: Insert operation
    insert_response = supabase.table('tld_strings').insert(data).execute()
    
    # ✅ CORRECT: Update operation  
    update_response = supabase.table('tld_strings').update(data).eq('id', tld_id).execute()
```

### Database Operations (Raw Client)

```python
from db.supabase_client import get_supabase

def create_application(data):
    supabase = get_supabase()
    
    # ✅ CORRECT: Use .table() directly
    response = supabase.table('tld_applications').insert(data).execute()
```

## ❌ Incorrect Usage (DO NOT USE)

### These patterns cause AttributeError

```python
# ❌ WRONG: Don't use .client.table() with the wrapper
supabase = get_supabase_client()
response = supabase.client.table('tld_strings').select('*').execute()  # ERROR!

# ❌ WRONG: Don't mix the two client types
from crewai_service.utils.supabase_client import get_supabase_client
from db.supabase_client import get_supabase

supabase1 = get_supabase_client()
supabase2 = get_supabase()
# This creates confusion about which client to use
```

## 🔧 Enhanced Wrapper Features

The enhanced wrapper (`crewai_service/utils/supabase_client.py`) provides:

1. **Automatic credential loading** from `/secrets` directory
2. **Error handling** with graceful fallbacks
3. **Logging** of all operations
4. **Enabled/disabled state** management
5. **Simplified `.table()` method** that works like the raw client

### Key Methods

```python
class SupabaseClient:
    def __init__(self):
        # Loads credentials from SUPABASE_URL / SUPABASE_SERVICE_KEY
        
    def table(self, table_name: str):
        # Direct access to table operations
        
    def store_tld_string(self, data):
        # Helper method for TLD string storage
        
    def get_tld_string_by_name(self, name):
        # Helper method for TLD string retrieval
```

## 🚨 Migration Guide

If you see this error:
```
AttributeError: 'SupabaseClient' object has no attribute 'table'
```

**Fix:** Remove `.client` from the call:
```python
# ❌ OLD (causes error)
supabase.client.table('tld_strings').select('*').execute()

# ✅ NEW (correct)
supabase.table('tld_strings').select('*').execute()
```

## 📁 File Organization

```
open-scrutiny/
├── crewai_service/
│   ├── utils/
│   │   └── supabase_client.py    # Enhanced wrapper (USE THIS)
│   ├── app.py                    # Uses wrapper client
│   └── workflow_queue.py         # Uses wrapper client
├── db/
│   ├── supabase_client.py        # Raw client (legacy)
│   ├── tld_application_store.py  # Uses raw client
│   └── evaluation_store.py       # Uses raw client
```

## 🔄 Common Operations

### Create Record
```python
# Both clients use the same pattern
data = {"tld_string": "example", "use_case": "testing"}
response = supabase.table('tld_strings').insert(data).execute()
```

### Read Records
```python
# Select all
response = supabase.table('tld_strings').select('*').execute()

# Select with filter
response = supabase.table('tld_strings').select('*').eq('tld_string', 'example').execute()

# Select single record
response = supabase.table('tld_strings').select('*').eq('id', tld_id).single().execute()
```

### Update Records
```python
update_data = {"status": "completed"}
response = supabase.table('tld_strings').update(update_data).eq('id', tld_id).execute()
```

### Delete Records
```python
response = supabase.table('tld_strings').delete().eq('id', tld_id).execute()
```

### Upsert Records
```python
data = {"tld_string": "example", "status": "updated"}
response = supabase.table('tld_strings').upsert(data, on_conflict='tld_string').execute()
```

## 🔍 Debugging Tips

### Check Client Type
```python
supabase = get_supabase_client()
print(f"Client type: {type(supabase)}")
print(f"Has .table method: {hasattr(supabase, 'table')}")
print(f"Has .client attribute: {hasattr(supabase, 'client')}")
```

### Check if Enabled
```python
supabase = get_supabase_client()
if supabase.enabled:
    print("✅ Supabase client is enabled")
else:
    print("❌ Supabase client is disabled (check credentials)")
```

### Error Handling
```python
try:
    response = supabase.table('tld_strings').select('*').execute()
    if response.data:
        print(f"Found {len(response.data)} records")
    else:
        print("No records found")
except Exception as e:
    print(f"Error: {e}")
```

## 📝 Best Practices

1. **Always use the appropriate client** for your module
2. **Import from the correct location** based on your directory
3. **Handle errors gracefully** with try/except blocks
4. **Check if client is enabled** before operations
5. **Use the simplified `.table()` method** - never `.client.table()`

## 🔧 Troubleshooting

### Common Issues

1. **AttributeError: 'SupabaseClient' object has no attribute 'table'**
   - **Cause:** Using old code that called `.client.table()`
   - **Fix:** Use `.table()` directly

2. **Supabase client not enabled**
   - **Cause:** Missing credentials in `/secrets` directory
   - **Fix:** Add `supabase_url.txt` and `supabase_key.txt` to `/secrets`

3. **Import errors**
   - **Cause:** Importing from wrong location
   - **Fix:** Use correct import path for your module

### Testing Client
```python
# Test script to verify client works
from crewai_service.utils.supabase_client import get_supabase_client

supabase = get_supabase_client()
if supabase.enabled:
    try:
        response = supabase.table('tld_strings').select('id').limit(1).execute()
        print("✅ Client working correctly")
    except Exception as e:
        print(f"❌ Client error: {e}")
else:
    print("❌ Client not enabled")
```

---

**Last Updated:** 2025-07-16  
**Version:** 1.0  
**Maintainer:** Development Team 