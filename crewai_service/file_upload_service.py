"""
File Upload Service for gTLD Application Documents
Handles document uploads, validation, and storage for application questions
"""

import os
import uuid
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import UploadFile, HTTPException
import aiofiles

from db.supabase_client import DatabaseSupabaseClient

class FileUploadService:
    def __init__(self):
        self.db_client = DatabaseSupabaseClient()
        self.upload_dir = Path("uploads/applications")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # File validation settings
        self.max_file_size = 25 * 1024 * 1024  # 25MB
        self.allowed_extensions = {
            '.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif'
        }
        self.allowed_mime_types = {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'image/jpeg',
            'image/png',
            'image/gif'
        }

    async def upload_files(
        self,
        application_id: str,
        question_id: str,
        files: List[UploadFile],
        document_type: Optional[str] = None,
        uploaded_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Upload files for a specific application question
        """
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        # Validate application exists
        supabase = self.db_client.client
        app_result = supabase.table('tld_applications').select('id').eq('id', application_id).execute()
        if not app_result.data:
            raise HTTPException(status_code=404, detail="Application not found")
        
        uploaded_files = []
        
        for file in files:
            try:
                uploaded_file = await self._process_single_file(
                    application_id=application_id,
                    question_id=question_id,
                    file=file,
                    document_type=document_type,
                    uploaded_by=uploaded_by
                )
                uploaded_files.append(uploaded_file)
            except Exception as e:
                # If any file fails, clean up already uploaded files
                for uploaded_file in uploaded_files:
                    await self._cleanup_file(uploaded_file['stored_filename'])
                raise HTTPException(status_code=400, detail=f"Failed to upload {file.filename}: {str(e)}")
        
        return uploaded_files

    async def _process_single_file(
        self,
        application_id: str,
        question_id: str,
        file: UploadFile,
        document_type: Optional[str] = None,
        uploaded_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process and validate a single file upload
        """
        # Validate file
        validation_errors = await self._validate_file(file)
        if validation_errors:
            raise ValueError(f"File validation failed: {', '.join(validation_errors)}")
        
        # Generate unique filename
        file_extension = Path(file.filename or '').suffix.lower()
        stored_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = self.upload_dir / stored_filename
        
        # Calculate file hash while reading
        file_hash = hashlib.sha256()
        file_size = 0
        
        # Save file to disk
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(8192):  # Read in 8KB chunks
                file_size += len(chunk)
                file_hash.update(chunk)
                await f.write(chunk)
        
        # Reset file position for potential re-reading
        await file.seek(0)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file.filename or '')
        
        # Store file metadata in database
        supabase = self.db_client.client
        file_record = {
            'application_id': application_id,
            'question_id': question_id,
            'document_type': document_type,
            'original_filename': file.filename,
            'stored_filename': stored_filename,
            'file_path': str(file_path),
            'file_size_bytes': file_size,
            'file_type': file_extension.lstrip('.').upper(),
            'mime_type': mime_type,
            'file_hash': file_hash.hexdigest(),
            'uploaded_by': uploaded_by,
            'validation_status': 'pending',
            'processing_status': 'uploaded'
        }
        
        result = supabase.table('application_file_uploads').insert(file_record).execute()
        if not result.data:
            # Clean up file if database insert fails
            await self._cleanup_file(stored_filename)
            raise ValueError("Failed to save file metadata to database")
        
        file_data = result.data[0]
        
        # Perform initial validation
        validation_status, validation_errors = await self._validate_file_content(file_path, document_type)
        
        # Update validation status
        supabase.table('application_file_uploads').update({
            'validation_status': validation_status,
            'validation_errors': validation_errors,
            'processed_at': datetime.utcnow().isoformat()
        }).eq('id', file_data['id']).execute()
        
        return {
            'id': file_data['id'],
            'original_filename': file.filename,
            'stored_filename': stored_filename,
            'file_path': str(file_path),
            'file_size_bytes': file_size,
            'validation_status': validation_status,
            'validation_errors': validation_errors
        }

    async def _validate_file(self, file: UploadFile) -> List[str]:
        """
        Validate file before processing
        """
        errors = []
        
        if not file.filename:
            errors.append("Filename is required")
            return errors
        
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.allowed_extensions:
            errors.append(f"File type {file_extension} not allowed. Allowed types: {', '.join(self.allowed_extensions)}")
        
        # Check file size
        if hasattr(file, 'size') and file.size and file.size > self.max_file_size:
            errors.append(f"File size {file.size} bytes exceeds maximum {self.max_file_size} bytes")
        
        # Check MIME type if available
        if file.content_type and file.content_type not in self.allowed_mime_types:
            errors.append(f"MIME type {file.content_type} not allowed")
        
        return errors

    async def _validate_file_content(self, file_path: Path, document_type: Optional[str]) -> tuple[str, List[str]]:
        """
        Validate file content after upload
        """
        errors = []
        
        # Basic file existence check
        if not file_path.exists():
            errors.append("File does not exist after upload")
            return 'invalid', errors
        
        # Check if file is not empty
        if file_path.stat().st_size == 0:
            errors.append("File is empty")
            return 'invalid', errors
        
        # Additional validation based on document type
        if document_type:
            if document_type == 'lei_certificate' and file_path.suffix.lower() == '.txt':
                # For LEI, check if it contains a 20-character alphanumeric string
                try:
                    content = file_path.read_text()
                    if not any(len(line.strip()) == 20 and line.strip().isalnum() for line in content.split('\n')):
                        errors.append("LEI certificate should contain a 20-character alphanumeric identifier")
                except Exception:
                    errors.append("Could not read LEI certificate content")
        
        # Return validation status
        if errors:
            return 'needs_review', errors
        else:
            return 'valid', []

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file and its database record
        """
        supabase = self.db_client.client
        
        # Get file record
        result = supabase.table('application_file_uploads').select('*').eq('id', file_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_record = result.data[0]
        
        # Delete file from disk
        file_path = Path(file_record['file_path'])
        if file_path.exists():
            file_path.unlink()
        
        # Delete database record
        delete_result = supabase.table('application_file_uploads').delete().eq('id', file_id).execute()
        
        return len(delete_result.data) > 0

    async def get_application_files(self, application_id: str) -> List[Dict[str, Any]]:
        """
        Get all files for an application
        """
        supabase = self.db_client.client
        
        result = supabase.table('application_file_uploads').select('*').eq('application_id', application_id).order('uploaded_at', desc=True).execute()
        
        return result.data or []

    async def _cleanup_file(self, stored_filename: str):
        """
        Clean up file from disk
        """
        file_path = self.upload_dir / stored_filename
        if file_path.exists():
            file_path.unlink()

# Global service instance
file_upload_service = FileUploadService()

