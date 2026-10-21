"""
Google Drive Export Service for TLD Reports

Automatically exports TLD feasibility reports to Google Drive using service account authentication.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import re

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False
    print("⚠️ Google APIs not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

from supabase import create_client
from db.tld_application_store import TldApplicationStore

logger = logging.getLogger(__name__)

class GoogleDriveExporter:
    def __init__(self):
        self.drive_service = None
        self.docs_service = None
        self.folder_id = None
        self.supabase = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize Google Drive and Docs services"""
        if not GOOGLE_APIS_AVAILABLE:
            logger.error("Google APIs not available. Cannot initialize Google Drive exporter.")
            return
            
        try:
            # Load service account credentials
            creds_path = self._get_service_account_path()
            if not creds_path or not creds_path.exists():
                logger.warning(f"Google service account file not found - Google Drive export disabled")
                return
                
            credentials = service_account.Credentials.from_service_account_file(
                str(creds_path),
                scopes=[
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/documents'
                ]
            )
            
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.docs_service = build('docs', 'v1', credentials=credentials)
            
            # Target folder for exported reports (shared drive / folder ID)
            self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
            
            # Initialize Supabase client
            self._initialize_supabase()
            
            logger.info("✅ Google Drive exporter initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive services: {e}")
    
    def _get_service_account_path(self) -> Optional[Path]:
        """Locate the Google service account JSON via GOOGLE_SERVICE_ACCOUNT_PATH."""
        env_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
        if env_path and Path(env_path).exists():
            return Path(env_path)
            
        return None
    
    def _initialize_supabase(self):
        """Initialize Supabase client using TldApplicationStore"""
        try:
            app_store = TldApplicationStore()
            self.supabase = app_store.supabase
            if self.supabase and self.supabase.is_enabled():
                logger.info("✅ Supabase client initialized via TldApplicationStore")
            else:
                logger.error("TldApplicationStore Supabase client not available")
                self.supabase = None
        except Exception as e:
            logger.error(f"Failed to initialize Supabase via TldApplicationStore: {e}")
            self.supabase = None
    
    def _find_reports_folder(self) -> Optional[str]:
        """Find the 'Real Strings Reports v1' folder in Google Drive"""
        if not self.drive_service:
            return None
            
        try:
            # Search for folder by name (with shared drive support)
            results = self.drive_service.files().list(
                q="name='Real Strings Reports v1' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"✅ Found 'Real Strings Reports v1' folder: {folder_id}")
                return folder_id
            else:
                logger.warning("'Real Strings Reports v1' folder not found. Will create it.")
                return self._create_reports_folder()
                
        except HttpError as e:
            logger.error(f"Error finding reports folder: {e}")
            return None
    
    def _create_reports_folder(self) -> Optional[str]:
        """Create the 'Real Strings Reports v1' folder"""
        if not self.drive_service:
            return None
            
        try:
            folder_metadata = {
                'name': 'Real Strings Reports v1',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"✅ Created 'Real Strings Reports v1' folder: {folder_id}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error creating reports folder: {e}")
            return None
    
    def _convert_markdown_to_docs_requests(self, markdown_content: str) -> list:
        """
        Convert markdown content to Google Docs API requests with proper rich text formatting
        """
        import re
        
        requests = []
        lines = markdown_content.split('\n')
        current_index = 1
        
        # First, insert all the text content (without markdown formatting)
        clean_text = ""
        for line in lines:
            # Remove markdown formatting for clean text insertion
            clean_line = line
            # Remove markdown headers
            clean_line = re.sub(r'^#{1,6}\s*', '', clean_line)
            # Remove bold markdown
            clean_line = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_line)
            # Remove bullet points
            clean_line = re.sub(r'^\s*[\*\-]\s*', '', clean_line)
            
            clean_text += clean_line + '\n'
        
        # Insert all clean text first
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': clean_text
            }
        })
        
        # Now apply formatting by finding patterns in the original text
        current_pos = 1
        
        for line in lines:
            clean_line = line
            clean_line = re.sub(r'^#{1,6}\s*', '', clean_line)
            clean_line = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_line)
            clean_line = re.sub(r'^\s*[\*\-]\s*', '', clean_line)
            clean_line_length = len(clean_line) + 1
            
            # Apply paragraph styles based on markdown headers
            if line.startswith('# '):
                # Main title
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': current_pos,
                            'endIndex': current_pos + clean_line_length - 1
                        },
                        'paragraphStyle': {
                            'namedStyleType': 'TITLE'
                        },
                        'fields': 'namedStyleType'
                    }
                })
            elif line.startswith('## '):
                # Section headers
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': current_pos,
                            'endIndex': current_pos + clean_line_length - 1
                        },
                        'paragraphStyle': {
                            'namedStyleType': 'HEADING_1'
                        },
                        'fields': 'namedStyleType'
                    }
                })
            elif line.startswith('### '):
                # Subsection headers
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': current_pos,
                            'endIndex': current_pos + clean_line_length - 1
                        },
                        'paragraphStyle': {
                            'namedStyleType': 'HEADING_2'
                        },
                        'fields': 'namedStyleType'
                    }
                })
            elif line.startswith('*   ') or line.startswith('- '):
                # Bullet points
                requests.append({
                    'createParagraphBullets': {
                        'range': {
                            'startIndex': current_pos,
                            'endIndex': current_pos + clean_line_length - 1
                        },
                        'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                    }
                })
            
            # Find and format bold text in the clean text
            original_line = line
            if '**' in original_line:
                # Find bold patterns in the original line and map to clean line
                bold_matches = re.finditer(r'\*\*(.*?)\*\*', original_line)
                clean_line_text = clean_line.rstrip('\n')
                
                for match in bold_matches:
                    bold_text = match.group(1)
                    if bold_text in clean_line_text:
                        # Find position of bold text in clean line
                        bold_start_in_clean = clean_line_text.find(bold_text)
                        if bold_start_in_clean != -1:
                            bold_start_pos = current_pos + bold_start_in_clean
                            bold_end_pos = bold_start_pos + len(bold_text)
                            
                            requests.append({
                                'updateTextStyle': {
                                    'range': {
                                        'startIndex': bold_start_pos,
                                        'endIndex': bold_end_pos
                                    },
                                    'textStyle': {
                                        'bold': True
                                    },
                                    'fields': 'bold'
                                }
                            })
            
            current_pos += clean_line_length
        
        return requests
    
    def _is_valid_report_for_tld(self, tld_string: str, report_data: Dict[str, Any]) -> bool:
        """Check if a report contains valid content for the specified TLD"""
        try:
            if not isinstance(report_data, dict):
                return False
                
            content = report_data.get('report_content', '')
            if not content or len(content) < 100:  # Too short to be a real report
                return False
            
            # Check if the report mentions the correct TLD in the first few lines
            first_500_chars = content[:500].lower()
            expected_tld = f'.{tld_string}'
            
            # Valid report should mention the correct TLD, not other TLDs
            if expected_tld.lower() in first_500_chars:
                # Make sure it's not a generic template mentioning other TLDs
                generic_indicators = ['.food', '.shop', '.test'] 
                other_tlds = [indicator for indicator in generic_indicators if indicator != expected_tld.lower()]
                
                # If it mentions other common template TLDs, it's probably generic
                for other_tld in other_tlds:
                    if other_tld in first_500_chars:
                        logger.debug(f"Skipping .{tld_string}: contains generic {other_tld} content")
                        return False
                
                return True
            else:
                logger.debug(f"Skipping .{tld_string}: doesn't mention correct TLD in content")
                return False
                
        except Exception as e:
            logger.error(f"Error validating report for .{tld_string}: {e}")
            return False
    
    def export_report_to_drive(self, tld_string: str, report_data: Dict[str, Any]) -> Optional[str]:
        """Export a single TLD report to Google Drive using Drive API"""
        if not self.drive_service or not self.folder_id:
            logger.error("Google Drive service not properly initialized")
            return None
            
        try:
            # Extract report content from the nested structure
            report_content = report_data.get('report_content', '')
            if not report_content:
                logger.warning(f"No report content found for {tld_string}")
                logger.debug(f"Report data structure: {report_data}")
                return None
            
            # Idempotency: if a document already exists for this TLD in the target
            # folder, return its URL instead of creating a duplicate.
            try:
                doc_title = f"{tld_string} evaluation"
                query = (
                    f"name = '{doc_title}' and trashed = false "
                    f"and mimeType = 'application/vnd.google-apps.document' "
                    f"and '{self.folder_id}' in parents"
                )
                existing = self.drive_service.files().list(
                    q=query,
                    fields='files(id,name,webViewLink)',
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                files = (existing or {}).get('files', [])
                if files:
                    doc_url = files[0].get('webViewLink')
                    logger.info(f"♻️  Reusing existing document for .{tld_string}: {doc_url}")
                    return doc_url
            except Exception as e:
                logger.debug(f"Existing doc lookup failed for .{tld_string} (continuing to create): {e}")

            # Create the document using Drive API
            doc_title = f"{tld_string} evaluation"
            
            file_metadata = {
                'name': doc_title,
                'mimeType': 'application/vnd.google-apps.document',
                'parents': [self.folder_id]
            }
            
            # Create empty Google Doc first (with shared drive support)
            doc = self.drive_service.files().create(
                body=file_metadata,
                fields='id,name,webViewLink',
                supportsAllDrives=True
            ).execute()
            
            doc_id = doc.get('documentId') or doc.get('id')
            doc_url = doc.get('webViewLink')
            
            # Add content using Docs API if available, otherwise just create empty doc
            if self.docs_service:
                try:
                    requests = self._convert_markdown_to_docs_requests(report_content)
                    if requests:
                        self.docs_service.documents().batchUpdate(
                            documentId=doc_id,
                            body={'requests': requests}
                        ).execute()
                        logger.info(f"✅ Added content to document for .{tld_string}")
                except Exception as e:
                    logger.warning(f"Could not add content to document for .{tld_string}: {e}")
                    logger.info(f"Document created but content addition failed - manual editing required")
            
            logger.info(f"✅ Exported report for .{tld_string} to Google Drive: {doc_url}")
            return doc_url
            
        except HttpError as e:
            logger.error(f"Error exporting report for {tld_string}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error exporting report for {tld_string}: {e}")
            return None
    
    def batch_export_all_reports(self) -> Dict[str, str]:
        """Export all existing reports to Google Drive (only real AI-generated reports)"""
        if not self.supabase:
            logger.error("Supabase not initialized")
            return {}
            
        try:
            # Get all TLD strings with generated reports
            response = self.supabase.table('tld_strings').select(
                'tld_string, generated_report'
            ).not_.is_('generated_report', 'null').execute()
            
            results = {}
            valid_reports = []
            skipped_reports = []
            
            # Filter out generic/placeholder reports
            for row in response.data:
                tld_string = row['tld_string']
                generated_report = row['generated_report']
                
                if self._is_valid_report_for_tld(tld_string, generated_report):
                    valid_reports.append(row)
                else:
                    skipped_reports.append(tld_string)
            
            total_valid = len(valid_reports)
            total_skipped = len(skipped_reports)
            
            logger.info(f"📊 Found {total_valid} valid reports, skipping {total_skipped} generic/placeholder reports")
            
            if skipped_reports:
                logger.info(f"⚠️ Skipped reports: {', '.join([f'.{tld}' for tld in skipped_reports[:10]])}")
                if len(skipped_reports) > 10:
                    logger.info(f"   ... and {len(skipped_reports) - 10} more")
            
            for i, row in enumerate(valid_reports, 1):
                tld_string = row['tld_string']
                generated_report = row['generated_report']
                
                logger.info(f"📄 Exporting {i}/{total_valid}: .{tld_string}")
                
                doc_url = self.export_report_to_drive(tld_string, generated_report)
                if doc_url:
                    results[tld_string] = doc_url
                else:
                    logger.warning(f"❌ Failed to export .{tld_string}")
                    
                # Add small delay to avoid rate limiting
                import time
                time.sleep(1)
            
            logger.info(f"✅ Batch export completed: {len(results)}/{total_valid} valid reports exported")
            return results
            
        except Exception as e:
            logger.error(f"Error during batch export: {e}")
            return {}
    
    def auto_export_new_report(self, tld_string: str) -> Optional[str]:
        """Automatically export a newly generated report (only if valid)"""
        if not self.supabase:
            logger.error("Supabase not initialized for auto-export")
            return None
            
        try:
            # Get the specific report
            response = self.supabase.table('tld_strings').select(
                'generated_report'
            ).eq('tld_string', tld_string).single().execute()
            
            if response.data and response.data.get('generated_report'):
                generated_report = response.data['generated_report']
                
                # Only export if it's a valid report for this TLD
                if self._is_valid_report_for_tld(tld_string, generated_report):
                    return self.export_report_to_drive(tld_string, generated_report)
                else:
                    logger.info(f"Skipping auto-export for .{tld_string}: contains generic/placeholder content")
                    return None
            else:
                logger.warning(f"No generated report found for {tld_string}")
                return None
                
        except Exception as e:
            logger.error(f"Error auto-exporting report for {tld_string}: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if the Google Drive exporter is properly configured and available"""
        return (
            GOOGLE_APIS_AVAILABLE and 
            self.drive_service is not None and 
            self.docs_service is not None and 
            self.folder_id is not None and
            self.supabase is not None
        )


# Global instance
drive_exporter = GoogleDriveExporter()


def export_report_to_google_drive(tld_string: str) -> Optional[str]:
    """Convenience function to export a report to Google Drive"""
    if drive_exporter.is_available():
        return drive_exporter.auto_export_new_report(tld_string)
    else:
        logger.warning("Google Drive exporter not available")
        return None


def batch_export_all_reports() -> Dict[str, str]:
    """Convenience function to batch export all reports"""
    if drive_exporter.is_available():
        return drive_exporter.batch_export_all_reports()
    else:
        logger.warning("Google Drive exporter not available")
        return {}