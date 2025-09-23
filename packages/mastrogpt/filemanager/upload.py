#--web true
"""
API Path: api/my/filemanagement/upload
This action handles file uploads to the server file system.
"""
import os
import json
import asyncio
import base64
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import mimetypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main asynchronous function for uploading files.
    
    Expected parameters:
    - files (list): Array of file objects with name, type, size, base64 data
    - destination_path (str, optional): Destination folder path
    - base_directory (str, optional): Base directory to restrict operations
    - overwrite (bool, optional): Whether to overwrite existing files
    
    Returns:
    - success (bool): Whether the operation was successful
    - message (str): Success or error message
    - uploaded_files (list): List of successfully uploaded files
    - failed_files (list): List of files that failed to upload
    """
    
    try:
        # Extract parameters
        files = args.get('files', [])
        destination_path = args.get('destination_path', '/')
        base_directory = args.get('base_directory', '/tmp/filemanager')
        overwrite = args.get('overwrite', False)
        max_file_size = args.get('max_file_size', 10 * 1024 * 1024)  # 10MB default
        
        # Validate required parameters
        if not files:
            return {
                'success': False,
                'error': 'MISSING_PARAMETER',
                'message': 'files parameter is required'
            }
        
        if not isinstance(files, list):
            return {
                'success': False,
                'error': 'INVALID_PARAMETER',
                'message': 'files must be an array'
            }
        
        # Sanitize and validate destination path
        try:
            dest_path_obj = Path(base_directory) / destination_path.lstrip('/')
            dest_path_resolved = dest_path_obj.resolve()
            base_path_resolved = Path(base_directory).resolve()
            
            # Security check: ensure the path is within the base directory
            if not str(dest_path_resolved).startswith(str(base_path_resolved)):
                return {
                    'success': False,
                    'error': 'SECURITY_VIOLATION',
                    'message': 'Destination path is outside allowed directory'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': 'INVALID_PATH',
                'message': f'Invalid destination path: {str(e)}'
            }
        
        # Ensure destination directory exists
        try:
            dest_path_resolved.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return {
                'success': False,
                'error': 'DIRECTORY_CREATE_ERROR',
                'message': f'Could not create destination directory: {str(e)}'
            }
        
        uploaded_files = []
        failed_files = []
        
        # Process each file
        for file_data in files:
            try:
                file_result = await process_single_file(
                    file_data, 
                    dest_path_resolved, 
                    base_path_resolved,
                    overwrite,
                    max_file_size
                )
                
                if file_result['success']:
                    uploaded_files.append(file_result)
                else:
                    failed_files.append(file_result)
                    
            except Exception as e:
                logger.error(f"Error processing file {file_data.get('name', 'unknown')}: {str(e)}")
                failed_files.append({
                    'success': False,
                    'name': file_data.get('name', 'unknown'),
                    'error': 'PROCESSING_ERROR',
                    'message': f'Error processing file: {str(e)}'
                })
        
        # Determine overall success
        total_files = len(files)
        successful_uploads = len(uploaded_files)
        
        if successful_uploads == total_files:
            message = f'Successfully uploaded {successful_uploads} file(s)'
            success = True
        elif successful_uploads > 0:
            message = f'Uploaded {successful_uploads} of {total_files} files. {len(failed_files)} failed.'
            success = True  # Partial success
        else:
            message = f'Failed to upload all {total_files} files'
            success = False
        
        logger.info(f"Upload operation completed: {successful_uploads}/{total_files} successful")
        
        return {
            'success': success,
            'message': message,
            'uploaded_files': uploaded_files,
            'failed_files': failed_files,
            'total_files': total_files,
            'successful_uploads': successful_uploads
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in upload action: {str(e)}")
        return {
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': f'Internal server error: {str(e)}'
        }

async def process_single_file(
    file_data: Dict[str, Any], 
    dest_path: Path, 
    base_path: Path,
    overwrite: bool,
    max_file_size: int
) -> Dict[str, Any]:
    """
    Process a single file upload.
    """
    try:
        # Extract file information
        name = file_data.get('name')
        file_type = file_data.get('type', '')
        size = file_data.get('size', 0)
        base64_data = file_data.get('base64')
        
        # Validate file data
        if not name:
            return {
                'success': False,
                'name': name,
                'error': 'INVALID_FILE_DATA',
                'message': 'File name is required'
            }
        
        if not base64_data:
            return {
                'success': False,
                'name': name,
                'error': 'INVALID_FILE_DATA',
                'message': 'File data is required'
            }
        
        # Validate file name
        if not is_valid_filename(name):
            return {
                'success': False,
                'name': name,
                'error': 'INVALID_FILENAME',
                'message': 'File name contains invalid characters'
            }
        
        # Check file size
        if size > max_file_size:
            return {
                'success': False,
                'name': name,
                'error': 'FILE_TOO_LARGE',
                'message': f'File size ({size} bytes) exceeds maximum allowed size ({max_file_size} bytes)'
            }
        
        # Create file path
        file_path = dest_path / name
        
        # Check if file already exists
        if file_path.exists() and not overwrite:
            return {
                'success': False,
                'name': name,
                'error': 'FILE_EXISTS',
                'message': f'File "{name}" already exists. Use overwrite=true to replace it.'
            }
        
        # Decode and write file
        try:
            file_content = base64.b64decode(base64_data)
            
            # Verify decoded size matches expected size
            if len(file_content) != size:
                logger.warning(f"Size mismatch for {name}: expected {size}, got {len(file_content)}")
            
            # Write file asynchronously
            await write_file_async(file_path, file_content)
            
            # Calculate relative path for response
            relative_path = str(file_path.relative_to(base_path))
            
            return {
                'success': True,
                'name': name,
                'path': f'/{relative_path}',
                'size': len(file_content),
                'type': file_type,
                'message': f'Successfully uploaded "{name}"'
            }
            
        except Exception as e:
            return {
                'success': False,
                'name': name,
                'error': 'WRITE_ERROR',
                'message': f'Failed to write file: {str(e)}'
            }
            
    except Exception as e:
        return {
            'success': False,
            'name': file_data.get('name', 'unknown'),
            'error': 'PROCESSING_ERROR',
            'message': f'Error processing file: {str(e)}'
        }

async def write_file_async(file_path: Path, content: bytes) -> None:
    """
    Asynchronously write file content.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, write_file_sync, file_path, content)

def write_file_sync(file_path: Path, content: bytes) -> None:
    """
    Synchronously write file content.
    """
    with open(file_path, 'wb') as f:
        f.write(content)

def is_valid_filename(filename: str) -> bool:
    """
    Validate filename for security and filesystem compatibility.
    """
    if not filename or filename in ['.', '..']:
        return False
    
    # Check for invalid characters
    invalid_chars = '<>:"/\\|?*'
    if any(char in filename for char in invalid_chars):
        return False
    
    # Check for reserved names on Windows
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    if filename.upper() in reserved_names:
        return False
    
    # Check length
    if len(filename) > 255:
        return False
    
    return True

# Entry point for Nuvolaris
def main_handler(args):
    """
    Synchronous wrapper for the async main function.
    This is the entry point that Nuvolaris will call.
    """
    return asyncio.run(main(args))

# For local testing
if __name__ == "__main__":
    # Test the function locally
    test_args = {
        'files': [
            {
                'name': 'test.txt',
                'type': 'text/plain',
                'size': 11,
                'base64': base64.b64encode(b'Hello World').decode('utf-8')
            }
        ],
        'destination_path': '/uploads',
        'base_directory': '/tmp/filemanager'
    }
    result = main_handler(test_args)
    print(json.dumps(result, indent=2))