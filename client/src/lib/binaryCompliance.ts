/**
 * BINARY COMPLIANCE CHECKS - SIMPLE CLIENT-SIDE VALIDATION
 * 
 * 🎯 WHAT THIS DOES:
 * Simple real-time validation that checks if a TLD string is available by comparing against:
 * 1. IANA Root Zone Database (existing TLDs)
 * 2. ICANN Blocked Domains (protected names)
 * 3. Reserved Names (RFC reserved names)
 * 4. Already Evaluated Strings (database check)
 * 
 * 🚀 HOW IT WORKS:
 * - Uses LOCAL DATA FILES in /public/data/ for instant validation (1-5ms)
 * - Uses SINGLE API call to check database for already evaluated strings
 * - Runs as user types in the submission modal
 * 
 * 📁 DATA FILES USED:
 * - /public/data/Iana Root DB.json - Array of {tld, type, explanation} (1571+ TLDs)
 * - /public/data/ICANN gTLD Blocked Domains.json - Array of blocked strings (50+ entries)
 * - /public/data/reserved_names.json - Complex object with reserved categories (156+ entries)
 * 
 * 🔍 DATABASE CHECK:
 * - Single optimized query to check if TLD string already exists in evaluations
 * - Uses fast .single() query with error handling for non-existent records
 * - Provides clear messaging about existing evaluations
 */

// Simple result types that match NewEvaluationModal expectations
export interface ComplianceResult {
  passes: boolean;
  reason?: string;
  category?: string;
  recommendation?: string;
  officialSource?: string;
}

export interface ComplianceResults {
  iana: ComplianceResult;
  blocked: ComplianceResult;
  reserved: ComplianceResult;
  existing: ComplianceResult;
  overall: ComplianceResult;
}

// Import supabase client for database checks
import { supabase } from './supabase'

// Simple cache to avoid re-loading files on every check
let dataCache: {
  ianaTlds: string[] | null;
  blockedNames: string[] | null;
  reservedNames: string[] | null;
  lastLoaded: number;
} = {
  ianaTlds: null,
  blockedNames: null,  
  reservedNames: null,
  lastLoaded: 0
};

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

/**
 * Load IANA TLDs from local data file
 * Returns array of TLD strings (lowercase, no dots)
 */
async function loadIanaTlds(): Promise<string[]> {
  const now = Date.now();
  
  // Use cache if fresh
  if (dataCache.ianaTlds && (now - dataCache.lastLoaded) < CACHE_DURATION) {
    return dataCache.ianaTlds;
  }

  try {
    const response = await fetch('/data/Iana%20Root%20DB.json');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const ianaData = await response.json();
    
    if (!Array.isArray(ianaData)) {
      throw new Error('Invalid IANA data format');
    }
    
    // Extract TLD strings, remove dots, make lowercase
    const tlds = ianaData.map((entry: any) => 
      entry.tld ? entry.tld.replace(/^\./, '').toLowerCase() : ''
    ).filter(tld => tld.length > 0);
    
    if (tlds.length < 1000) {
      throw new Error(`Too few TLDs loaded: ${tlds.length}`);
    }
    
    dataCache.ianaTlds = tlds;
    dataCache.lastLoaded = now;
    return tlds;
  } catch (error) {
    console.error('❌ Failed to load IANA data:', error);
    throw new Error('IANA database unavailable');
  }
}

/**
 * Load blocked names from local data file  
 * Returns array of blocked strings (lowercase)
 */
async function loadBlockedNames(): Promise<string[]> {
  const now = Date.now();
  
  // Use cache if fresh
  if (dataCache.blockedNames && (now - dataCache.lastLoaded) < CACHE_DURATION) {
    return dataCache.blockedNames;
  }

  try {
    const response = await fetch('/data/ICANN%20gTLD%20Blocked%20Domains.json');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const blockedData = await response.json();
    
    if (!Array.isArray(blockedData)) {
      throw new Error('Invalid blocked names format');
    }
    
    const blockedNames = blockedData.map(name => name.toLowerCase());
    
    dataCache.blockedNames = blockedNames;
    dataCache.lastLoaded = now;
    return blockedNames;
  } catch (error) {
    console.error('❌ Failed to load blocked names:', error);
    throw new Error('Blocked names list unavailable');
  }
}

/**
 * Load reserved names from local data file
 * Returns array of reserved strings (lowercase) from all categories
 */
async function loadReservedNames(): Promise<string[]> {
  const now = Date.now();
  
  // Use cache if fresh
  if (dataCache.reservedNames && (now - dataCache.lastLoaded) < CACHE_DURATION) {
    return dataCache.reservedNames;
  }

  try {
    const response = await fetch('/data/reserved_names.json');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const reservedData = await response.json();
    
    if (!reservedData.reserved_categories) {
      throw new Error('Invalid reserved names format');
    }
    
    // Extract all names from all categories
    const allReservedNames: string[] = [];
    Object.values(reservedData.reserved_categories).forEach((category: any) => {
      if (category.entries && Array.isArray(category.entries)) {
        allReservedNames.push(...category.entries.map((name: string) => name.toLowerCase()));
      }
    });
    
    if (allReservedNames.length < 50) {
      throw new Error(`Too few reserved names loaded: ${allReservedNames.length}`);
    }
    
    dataCache.reservedNames = allReservedNames;
    dataCache.lastLoaded = now;
    return allReservedNames;
  } catch (error) {
    console.error('❌ Failed to load reserved names:', error);
    throw new Error('Reserved names list unavailable');
  }
}

/**
 * Check if TLD string already exists in database (already evaluated)
 * Returns true if the string has been evaluated before
 */
async function checkExistingEvaluation(tldString: string): Promise<{exists: boolean, status?: string, id?: string}> {
  try {
    const { data, error } = await supabase
      .from('tld_strings')
      .select('id, overall_status, created_at')
      .eq('tld_string', tldString.toLowerCase())
      .single();

    if (error) {
      // PGRST116 means no rows found, which is what we want (string not evaluated yet)
      if (error.code === 'PGRST116') {
        return { exists: false };
      }
      throw error;
    }

    // String exists in database
    return {
      exists: true,
      status: data.overall_status,
      id: data.id
    };
  } catch (error) {
    console.error('❌ Failed to check existing evaluations:', error);
    // On error, assume string doesn't exist to avoid blocking valid submissions
    return { exists: false };
  }
}

/**
 * Check for confusing characters and mixed scripts that could cause IDN homograph issues
 * Based on ICANN IDN Guidelines and Unicode Consortium's confusables.txt
 * 
 * @param tldString - The TLD string to check (lowercase, no dots)
 * @returns true if the string contains potentially confusing characters
 */
function hasConfusingCharacters(tldString: string): boolean {
  // 1. Check for non-ASCII characters (ICANN requires special approval for IDN TLDs)
  if (!/^[a-z0-9-]+$/.test(tldString)) {
    return true;
  }

  // 2. Check for mixed digit/letter combinations that could be confusing
  // Based on ICANN's rejection of strings that could be mistaken for IP addresses or version numbers
  const confusingMixedPatterns = [
    /^[0-9]+[a-z]+$/,     // Numbers followed by letters (e.g., "123abc")
    /^[a-z]+[0-9]+$/,     // Letters followed by numbers (e.g., "abc123")
    /^[0-9][a-z][0-9]/,   // Alternating number-letter-number (e.g., "1a2")
    /^[a-z][0-9][a-z]/,   // Alternating letter-number-letter (e.g., "a1b")
    /^[il1o0]+$/i,        // Only confusing characters (l, i, 1, o, 0)
    /^[il1o0]+[0-9]+$/i,  // Confusing chars + numbers
    /^[0-9]+[il1o0]+$/i,  // Numbers + confusing chars
  ];

  for (const pattern of confusingMixedPatterns) {
    if (pattern.test(tldString)) {
      return true;
    }
  }

  // 3. Check for strings that could be confused with common protocols or system names
  const protocolLikePatterns = [
    /^(www|ftp|mail|smtp|pop|imap|dns|dhcp|http|https)\d*$/i,
    /^(localhost|local|home|corp|internal|admin)\d*$/i,
    /^v\d+$/,                    // Version numbers (v1, v2, etc.)
    /^\d+\.\d+$/,               // Version-like (1.0, 2.1, etc.) - dots not allowed but check anyway
    /^(test|dev|staging|prod)\d*$/i,  // Environment names
  ];

  for (const pattern of protocolLikePatterns) {
    if (pattern.test(tldString)) {
      return true;
    }
  }

  // 4. Check for strings that could be confused with file extensions
  const fileExtensionPatterns = [
    /^(exe|com|bat|cmd|scr|pif|dll|sys|ini|tmp|log|txt|doc|pdf|zip|rar)$/i,
    /^(js|py|rb|go|rs|c|h|css|xml|sql|php|asp|jsp|htm)$/i,  // Programming/web file extensions
    /^(bin|obj|lib|out|app|dmg|pkg|deb|rpm|msi|iso)$/i,     // Binary/installer extensions
  ];

  for (const pattern of fileExtensionPatterns) {
    if (pattern.test(tldString)) {
      return true;
    }
  }

  // 5. Check for potentially misleading length patterns
  // Very short (could be confused with country codes) or very long (user confusion)
  if (tldString.length === 1) {
    return true; // Single letter TLDs could be confusing
  }
  
  if (tldString.length > 63) {
    return true; // DNS label length limit
  }

  // 6. Check for repeated patterns that could be confusing
  if (/^(.)\1{4,}$/.test(tldString)) {
    return true; // 5 or more repeated characters (aaaaa, 11111)
  }

  // 7. Check for common typos of existing TLDs that could cause confusion
  const commonTldTypos = [
    'con', 'comm', 'coom', 'co', 'c0m',  // .com variations
    'ogr', 'org', 'orgg',               // .org variations  
    'nte', 'nett', 'n3t',               // .net variations
    'giv', 'g0v',                       // .gov variations
    'eud', 'ed', 'eduu',                // .edu variations
  ];

  if (commonTldTypos.includes(tldString)) {
    return true;
  }

  return false;
}

/**
 * MAIN FUNCTION: Check TLD against all compliance rules
 * 
 * This is the ONLY function that should be called from NewEvaluationModal.tsx
 * 
 * @param tldString - The TLD to check (with or without leading dot)
 * @returns ComplianceResults object with individual and overall results
 */
export async function checkBinaryCompliance(tldString: string): Promise<ComplianceResults> {
  // Clean input: remove dots, make lowercase, trim
  const cleanTld = tldString.replace(/^\.+/, '').toLowerCase().trim();
  
  if (!cleanTld) {
    const errorResult: ComplianceResult = { passes: false, reason: 'TLD string cannot be empty' };
    return {
      iana: errorResult,
      blocked: errorResult,
      reserved: errorResult,
      existing: errorResult,
      overall: errorResult
    };
  }

  try {
    // Load all data in parallel for speed
    const [ianaTlds, blockedNames, reservedNames, existingCheck] = await Promise.all([
      loadIanaTlds(),
      loadBlockedNames(), 
      loadReservedNames(),
      checkExistingEvaluation(cleanTld)
    ]);

    // 1. IANA CHECK: Passes if TLD does NOT exist (available for application)
    const ianaExists = ianaTlds.includes(cleanTld);
    const ianaResult: ComplianceResult = {
      passes: !ianaExists,
      reason: ianaExists 
        ? `TLD '.${cleanTld}' already exists in IANA Root Zone`
        : `TLD '.${cleanTld}' is available (not in IANA database)`,
      category: 'IANA Database',
      officialSource: 'IANA Root Zone Database'
    };

    // 2. BLOCKED CHECK: Passes if TLD is NOT in blocked list
    const isBlocked = blockedNames.includes(cleanTld);
    const blockedResult: ComplianceResult = {
      passes: !isBlocked,
      reason: isBlocked
        ? `TLD '.${cleanTld}' is in ICANN blocked domains list`
        : `TLD '.${cleanTld}' is not blocked`,
      category: 'Blocked Names',
      officialSource: 'ICANN Blocked Domains List'
    };

    // 3. RESERVED CHECK: Passes if TLD is NOT reserved
    const isReserved = reservedNames.includes(cleanTld);
    const reservedResult: ComplianceResult = {
      passes: !isReserved,
      reason: isReserved
        ? `TLD '.${cleanTld}' is reserved per RFC specifications`
        : `TLD '.${cleanTld}' is not reserved`,
      category: 'Reserved Names',
      officialSource: 'RFC 6761/2606 Reserved Names'
    };

    // 4. EXISTING EVALUATION CHECK: Passes if TLD has NOT been evaluated before
    const existingResult: ComplianceResult = {
      passes: !existingCheck.exists,
      reason: existingCheck.exists
        ? `TLD '.${cleanTld}' has already been evaluated (Status: ${existingCheck.status})`
        : `TLD '.${cleanTld}' has not been evaluated yet`,
      category: 'Already Evaluated',
      officialSource: 'TLD Evaluation Database'
    };

    // Add special check for two-letter domains (country code conflicts)
    if (cleanTld.length === 2 && /^[a-z]{2}$/.test(cleanTld)) {
      blockedResult.passes = false;
      blockedResult.reason = `TLD '.${cleanTld}' is a two-letter domain (country code conflict risk)`;
      blockedResult.category = 'Two-Letter Domain';
      blockedResult.officialSource = 'ISO 3166-1 Country Code Policy';
    }

    // Add check for all-digit TLDs (ICANN policy - rejected to avoid confusion with IPv4)
    if (/^\d+$/.test(cleanTld)) {
      blockedResult.passes = false;
      blockedResult.reason = `TLD '.${cleanTld}' is all-digit (rejected by ICANN to avoid IPv4/numeric confusion)`;
      blockedResult.category = 'All-Digit Domain';
      blockedResult.officialSource = 'ICANN All-Digit TLD Policy';
    }

    // Add check for mixed scripts and confusing characters (IDN homograph prevention)
    if (hasConfusingCharacters(cleanTld)) {
      blockedResult.passes = false;
      blockedResult.reason = `TLD '.${cleanTld}' contains potentially confusing characters or mixed scripts`;
      blockedResult.category = 'Mixed Script/Confusing Characters';
      blockedResult.officialSource = 'ICANN IDN Guidelines';
    }

    // OVERALL RESULT: Must pass ALL individual checks
    const allPassed = ianaResult.passes && blockedResult.passes && reservedResult.passes && existingResult.passes;
    const overallResult: ComplianceResult = {
      passes: allPassed,
      reason: !ianaResult.passes ? ianaResult.reason :
              !blockedResult.passes ? blockedResult.reason :
              !reservedResult.passes ? reservedResult.reason :
              !existingResult.passes ? existingResult.reason :
              `TLD '.${cleanTld}' passes all binary compliance checks`
    };

    return {
      iana: ianaResult,
      blocked: blockedResult,
      reserved: reservedResult,
      existing: existingResult,
      overall: overallResult
    };

  } catch (error) {
    console.error('🚨 Binary compliance check failed:', error);
    const errorMessage = error instanceof Error ? error.message : 'Validation unavailable';
    const errorResult: ComplianceResult = { 
      passes: false, 
      reason: `Validation failed: ${errorMessage}` 
    };
    
    return {
      iana: errorResult,
      blocked: errorResult,
      reserved: errorResult,
      existing: errorResult,
      overall: { passes: false, reason: '🚨 Validation services unavailable' }
    };
  }
}

/**
 * Clear cache (useful for development/testing)
 */
export function clearComplianceCache(): void {
  dataCache = {
    ianaTlds: null,
    blockedNames: null,
    reservedNames: null,
    lastLoaded: 0
  };
  console.log('🧹 Binary compliance cache cleared');
}

/**
 * DEVELOPER NOTES:
 * 
 * 🎯 SIMPLE ARCHITECTURE:
 * - ONE main function: checkBinaryCompliance()
 * - THREE data loaders: loadIanaTlds(), loadBlockedNames(), loadReservedNames()
 * - ONE cache object for performance
 * - THREE files in /public/data/
 * 
 * ✅ HOW TO MAINTAIN:
 * - Update data files in /public/data/ when ICANN lists change
 * - This code should rarely need changes
 * - If validation is broken, check data files first
 * 
 * ❌ WHAT NOT TO DO:
 * - Add API calls (causes timeouts)
 * - Make this more complex (confuses engineers)  
 * - Add CrewAI workflows (this is for instant feedback)
 * - Change the function signature (breaks NewEvaluationModal)
 * 
 * 🔧 TESTING:
 * - Test with "com" (should fail IANA check - already exists)
 * - Test with "test" (should fail reserved check - RFC reserved)
 * - Test with "olympic" (should fail blocked check - protected name)
 * - Test with "us" (should fail two-letter check - country code)
 * - Test with "123" (should fail all-digit check - IPv4 confusion)
 * - Test with "l23" (should fail confusing characters - looks like 123)
 * - Test with any previously evaluated string (should fail existing check)
 * - Test with "newstring" (should pass all checks)
 */