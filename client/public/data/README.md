# Client Data Files

## Purpose

These data files are used for **real-time binary compliance checks** in the TLD evaluation modal. They provide instant validation as users type, without requiring API calls to the backend.

## ⚠️ CRITICAL: DO NOT REMOVE OR MODIFY

These files are essential for the user experience. Removing them will break real-time validation and cause timeouts.

## Files

### Iana Root DB.json (225KB)
- **Source**: Official IANA Root Zone Database
- **Content**: 1571 existing TLDs with metadata
- **Usage**: Check if a TLD already exists in the IANA database
- **Format**: Array of objects with `tld`, `type`, `explanation` fields

### reserved_names.json (6KB)
- **Source**: ICANN Specification 5 and RFC 6761
- **Content**: 156 reserved names across multiple categories
- **Usage**: Check if a TLD is reserved by ICANN policy
- **Format**: Object with `reserved_categories` containing arrays of names

### ICANN gTLD Blocked Domains.json (1KB)
- **Source**: ICANN gTLD Blocked Domains List
- **Content**: 50+ blocked domain names
- **Usage**: Check if a TLD is in the ICANN blocked list
- **Format**: Array of blocked name strings

## Architecture Decision

**Why Local Files Instead of API Calls?**

1. **Performance**: 1-5ms vs 100-8000ms response time
2. **Reliability**: No network dependencies or timeouts
3. **User Experience**: Instant feedback as users type
4. **Offline Capability**: Works even when backend is down

## History

Previously, these checks used API calls which caused:
- 8-second timeouts when backend was unavailable
- Every TLD appearing as "already exists"
- Poor user experience with delayed feedback

**Fixed**: July 2025 - Moved to local data files for instant validation.

## Maintenance

- **Update Frequency**: Quarterly (when IANA data changes)
- **Update Process**: 
  1. Update files in `/data/` directory
  2. Copy to `client/public/data/`
  3. Test validation functions
- **Validation**: Functions include inline tests to verify data integrity

## Testing

The validation functions include automatic tests to ensure:
- Data files are loaded correctly
- Critical entries are present
- File sizes are reasonable

If these tests fail, the functions will throw descriptive errors rather than silently failing. 