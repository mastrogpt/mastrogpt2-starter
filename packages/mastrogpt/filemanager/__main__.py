#--kind python:default
#--web true
#--param S3_HOST $S3_HOST
#--param S3_PORT $S3_PORT
#--param S3_ACCESS_KEY $S3_ACCESS_KEY
#--param S3_SECRET_KEY $S3_SECRET_KEY
#--param S3_BUCKET_DATA $S3_BUCKET_DATA
#--param S3_API_URL $S3_API_URL

import sys
import os
import json
import asyncio
import traceback
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to import the operation modules
delete_module = None
rename_module = None
search_module = None
download_module = None

try:
    import delete as delete_module
    logger.info("Successfully imported delete module")
except ImportError as e:
    logger.warning(f"Could not import delete module: {e}")

try:
    import rename as rename_module
    logger.info("Successfully imported rename module")
except ImportError as e:
    logger.warning(f"Could not import rename module: {e}")

try:
    import search as search_module
    logger.info("Successfully imported search module")
except ImportError as e:
    logger.warning(f"Could not import search module: {e}")

try:
    import download as download_module
    logger.info("Successfully imported download module")
except ImportError as e:
    logger.warning(f"Could not import download module: {e}")

def get_s3_parameters() -> Dict[str, str]:
    """Extract S3 parameters from environment variables."""
    s3_params = {}
    param_keys = ['S3_HOST', 'S3_PORT', 'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_BUCKET_DATA', 'S3_API_URL']
    
    for key in param_keys:
        value = os.environ.get(key)
        if value:
            s3_params[key] = value
            logger.info(f"Found S3 parameter {key}: {'***' if 'KEY' in key else value}")
    
    return s3_params

def handle_rename(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle rename operations with full S3 support."""
    
    print("=" * 80)
    print("MAIN HANDLER: RENAME OPERATION")
    print("=" * 80)
    
    try:
        logger.info(f"Executing rename with args: {args}")
        
        # Extract S3 parameters and add them to args if missing
        s3_params = ['S3_HOST', 'S3_PORT', 'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_BUCKET_DATA', 'S3_API_URL']
        for param in s3_params:
            if param not in args:
                env_value = os.environ.get(param)
                if env_value:
                    args[param] = env_value
                    print(f"MAIN HANDLER: Added {param} from environment")
        
        # Force S3 rename support
        args['s3_rename_supported'] = True
        args['force_s3_rename'] = True
        
        print(f"MAIN HANDLER: S3 params available: {[p for p in s3_params if args.get(p)]}")
        
        # Check if rename module is available
        if not rename_module or not hasattr(rename_module, 'main'):
            print("MAIN HANDLER: ERROR - Rename module not available")
            return {
                "success": False,
                "error": "Rename module not available",
                "operation": "rename"
            }
        
        print("MAIN HANDLER: Calling rename module...")
        
        # Call the rename module directly - NO event loop creation
        result = rename_module.main(args)
        
        print(f"MAIN HANDLER: Rename module returned: {type(result)}")
        print(f"MAIN HANDLER: Result content: {json.dumps(result, indent=2, default=str)}")
        
        # Ensure proper response format
        if result and isinstance(result, dict):
            # Add operation metadata
            result['operation'] = 'rename'
            result['handler'] = 'main_filemanager'
            result['s3_supported'] = True
            
            if result.get('success'):
                logger.info("MAIN HANDLER: ✅ Rename operation completed successfully")
            else:
                logger.error(f"MAIN HANDLER: ❌ Rename operation failed: {result.get('error', 'Unknown error')}")
            
            return result
        else:
            print("MAIN HANDLER: ERROR - Invalid result from rename module")
            return {
                "success": False,
                "error": "Rename module returned invalid result",
                "operation": "rename"
            }
            
    except Exception as e:
        logger.error(f"MAIN HANDLER: Exception in rename: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "error": f"Rename handler error: {str(e)}",
            "operation": "rename",
            "timestamp": datetime.now().isoformat()
        }

def fallback_rename_with_debug(args: Dict[str, Any], debug_info: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback rename with debug information."""
    try:
        debug_info["step"] = "fallback"
        debug_info["execution_path"].append("fallback_start")
        
        logger.info("=== FALLBACK RENAME START ===")
        
        old_path = args.get('old_path', '').strip()
        new_name = args.get('new_name', '').strip()
        base_directory = args.get('base_directory', '/tmp/filemanager')
        
        debug_info["fallback_params"] = {
            "old_path": old_path,
            "new_name": new_name,
            "base_directory": base_directory
        }
        
        logger.info(f"Fallback params: {debug_info['fallback_params']}")
        
        if not old_path or not new_name:
            debug_info["errors"].append("Missing required params in fallback")
            return create_debug_error_response(400, "old_path and new_name are required", debug_info)
        
        # Validate new name
        debug_info["execution_path"].append("fallback_validation")
        if not is_valid_filename(new_name):
            debug_info["errors"].append("Invalid filename in fallback")
            return create_debug_error_response(400, f"Invalid filename: {new_name}", debug_info)
        
        # Setup paths
        debug_info["execution_path"].append("fallback_path_setup")
        base_path = Path(base_directory).resolve()
        
        # Create base directory if it doesn't exist
        if not base_path.exists():
            logger.info(f"Creating base directory: {base_path}")
            base_path.mkdir(parents=True, exist_ok=True)
        
        # Clean old path
        old_path_clean = old_path.lstrip('/')
        old_path_obj = base_path / old_path_clean
        
        # Try to resolve the path
        try:
            old_path_resolved = old_path_obj.resolve()
        except Exception as path_error:
            debug_info["errors"].append(f"Path resolution failed: {str(path_error)}")
            return create_debug_error_response(500, f"Path resolution failed: {str(path_error)}", debug_info)
        
        debug_info["fallback_paths"] = {
            "base_path": str(base_path),
            "old_path_obj": str(old_path_obj),
            "old_path_resolved": str(old_path_resolved),
            "old_path_exists": old_path_resolved.exists()
        }
        
        logger.info(f"Fallback paths: {debug_info['fallback_paths']}")
        
        # Security check
        debug_info["execution_path"].append("fallback_security_check")
        if not str(old_path_resolved).startswith(str(base_path)):
            debug_info["errors"].append("Path outside allowed directory")
            return create_debug_error_response(403, "Path outside allowed directory", debug_info)
        
        # Check source exists
        debug_info["execution_path"].append("fallback_source_check")
        if not old_path_resolved.exists():
            debug_info["errors"].append(f"Source not found: {old_path_resolved}")
            
            # List directory contents for debugging
            parent_dir = old_path_resolved.parent
            if parent_dir.exists():
                try:
                    contents = list(parent_dir.iterdir())
                    debug_info["parent_directory_contents"] = [str(p.name) for p in contents]
                    logger.info(f"Parent directory contents: {debug_info['parent_directory_contents']}")
                except:
                    debug_info["parent_directory_contents"] = "Could not list"
            
            return create_debug_error_response(404, f"Source not found: {old_path}", debug_info)
        
        # Create new path
        debug_info["execution_path"].append("fallback_new_path")
        new_path_obj = old_path_resolved.parent / new_name
        
        try:
            new_path_resolved = new_path_obj.resolve()
        except Exception as new_path_error:
            debug_info["errors"].append(f"New path resolution failed: {str(new_path_error)}")
            return create_debug_error_response(500, f"New path resolution failed: {str(new_path_error)}", debug_info)
        
        debug_info["new_path_info"] = {
            "new_path_obj": str(new_path_obj),
            "new_path_resolved": str(new_path_resolved),
            "new_path_exists": new_path_obj.exists()
        }
        
        # Security check for new path
        if not str(new_path_resolved).startswith(str(base_path)):
            debug_info["errors"].append("New path outside allowed directory")
            return create_debug_error_response(403, "New path outside allowed directory", debug_info)
        
        # Check destination doesn't exist
        if new_path_obj.exists():
            debug_info["errors"].append(f"Destination already exists: {new_name}")
            return create_debug_error_response(409, f"Destination already exists: {new_name}", debug_info)
        
        # Get info before rename
        debug_info["execution_path"].append("fallback_file_info")
        is_directory = old_path_resolved.is_dir()
        old_name = old_path_resolved.name
        
        try:
            file_size = old_path_resolved.stat().st_size if old_path_resolved.is_file() else None
        except Exception as stat_error:
            debug_info["errors"].append(f"Could not get file size: {str(stat_error)}")
            file_size = None
        
        debug_info["file_info"] = {
            "is_directory": is_directory,
            "old_name": old_name,
            "file_size": file_size
        }
        
        # Perform rename
        debug_info["execution_path"].append("fallback_rename_operation")
        try:
            logger.info(f"Attempting rename: {old_path_resolved} -> {new_path_obj}")
            os.rename(str(old_path_resolved), str(new_path_obj))
            logger.info("✅ Fallback rename successful")
        except PermissionError as e:
            debug_info["errors"].append(f"Permission error: {str(e)}")
            return create_debug_error_response(403, f"Permission denied: {str(e)}", debug_info)
        except FileExistsError as e:
            debug_info["errors"].append(f"File exists error: {str(e)}")
            return create_debug_error_response(409, f"Destination already exists: {str(e)}", debug_info)
        except OSError as e:
            debug_info["errors"].append(f"OS error: {str(e)}")
            return create_debug_error_response(500, f"Filesystem error: {str(e)}", debug_info)
        except Exception as e:
            debug_info["errors"].append(f"Rename operation failed: {str(e)}")
            return create_debug_error_response(500, f"Rename operation failed: {str(e)}", debug_info)
        
        # Calculate relative paths
        debug_info["execution_path"].append("fallback_success")
        try:
            relative_old_path = str(Path(old_path_clean))
            relative_new_path = str(new_path_obj.relative_to(base_path))
        except Exception as path_calc_error:
            debug_info["errors"].append(f"Path calculation error: {str(path_calc_error)}")
            relative_old_path = old_path_clean
            relative_new_path = new_name
        
        success_result = {
            'success': True,
            'message': f'Successfully renamed "{old_name}" to "{new_name}" (fallback)',
            'operation': 'rename',
            'old_path': f'/{relative_old_path}',
            'old_name': old_name,
            'new_path': f'/{relative_new_path}',
            'new_name': new_name,
            'type': 'folder' if is_directory else 'file',
            'size': file_size,
            'renamed_at': datetime.now().isoformat(),
            'method': 'fallback',
            'debug_info': debug_info
        }
        
        logger.info(f"✅ Fallback rename completed: {json.dumps(success_result, indent=2, default=str)}")
        return success_result
        
    except Exception as e:
        debug_info["execution_path"].append("fallback_exception")
        debug_info["errors"].append(f"Fallback exception: {str(e)}")
        logger.error(f"Fallback rename failed: {str(e)}")
        logger.error(traceback.format_exc())
        return create_debug_error_response(500, f"Fallback rename failed: {str(e)}", debug_info)

def create_debug_error_response(status_code: int, message: str, debug_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create error response with debug information."""
    logger.error(f"ERROR {status_code}: {message}")
    logger.error(f"Debug info: {json.dumps(debug_info, indent=2, default=str)}")
    
    return {
        'success': False,
        'error': message,
        'status_code': status_code,
        'operation': 'rename',
        'timestamp': datetime.now().isoformat(),
        'debug_info': debug_info
    }

def is_valid_filename(filename: str) -> bool:
    """Basic filename validation with logging."""
    logger.info(f"Validating filename: '{filename}'")
    
    if not filename or filename.strip() == '':
        logger.error("Filename is empty")
        return False
    
    filename = filename.strip()
    
    # Check for directory references
    if filename in ['.', '..']:
        logger.error("Filename is directory reference")
        return False
    
    # Check for invalid characters
    invalid_chars = '<>:"/\\|?*'
    found_invalid = [char for char in invalid_chars if char in filename]
    if found_invalid:
        logger.error(f"Filename contains invalid characters: {found_invalid}")
        return False
    
    # Check for control characters
    control_chars = [char for char in filename if ord(char) < 32]
    if control_chars:
        logger.error(f"Filename contains control characters: {control_chars}")
        return False
    
    # Check length
    if len(filename.encode('utf-8')) > 255:
        logger.error("Filename too long")
        return False
    
    logger.info("Filename is valid")
    return True

def get_s3_parameters() -> Dict[str, str]:
    """Extract S3 parameters from environment variables with logging."""
    s3_params = {}
    param_keys = ['S3_HOST', 'S3_PORT', 'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_BUCKET_DATA', 'S3_API_URL']
    
    logger.info("=== S3 PARAMETER EXTRACTION ===")
    for key in param_keys:
        value = os.environ.get(key)
        if value:
            s3_params[key] = value
            logger.info(f"Found S3 parameter {key}: {'***' if 'KEY' in key else value}")
        else:
            logger.info(f"S3 parameter {key} not found")
    
    logger.info(f"Total S3 parameters found: {len(s3_params)}")
    return s3_params

def fallback_rename(args: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback rename implementation using basic filesystem operations."""
    try:
        logger.info("=== FALLBACK RENAME START ===")
        
        old_path = args.get('old_path', '').strip()
        new_name = args.get('new_name', '').strip()
        base_directory = args.get('base_directory', '/tmp/filemanager')
        
        if not old_path or not new_name:
            return create_error_response(400, "old_path and new_name are required")
        
        # Validate new name
        if not is_valid_filename(new_name):
            return create_error_response(400, "Invalid filename")
        
        # Setup paths
        base_path = Path(base_directory).resolve()
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Clean old path
        old_path_clean = old_path.lstrip('/')
        old_path_obj = base_path / old_path_clean
        old_path_resolved = old_path_obj.resolve()
        
        logger.info(f"Fallback rename: {old_path_resolved} -> {new_name}")
        
        # Security check
        if not str(old_path_resolved).startswith(str(base_path)):
            return create_error_response(403, "Path outside allowed directory")
        
        # Check source exists
        if not old_path_resolved.exists():
            return create_error_response(404, f"Source not found: {old_path}")
        
        # Create new path
        new_path_obj = old_path_resolved.parent / new_name
        new_path_resolved = new_path_obj.resolve()
        
        # Security check for new path
        if not str(new_path_resolved).startswith(str(base_path)):
            return create_error_response(403, "New path outside allowed directory")
        
        # Check destination doesn't exist
        if new_path_obj.exists():
            return create_error_response(409, f"Destination already exists: {new_name}")
        
        # Get info before rename
        is_directory = old_path_resolved.is_dir()
        old_name = old_path_resolved.name
        file_size = old_path_resolved.stat().st_size if old_path_resolved.is_file() else None
        
        # Perform rename
        os.rename(str(old_path_resolved), str(new_path_obj))
        
        # Calculate relative paths
        relative_old_path = str(old_path_resolved.relative_to(base_path))
        relative_new_path = str(new_path_obj.relative_to(base_path))
        
        logger.info(f"✅ Fallback rename successful: {old_name} -> {new_name}")
        
        return {
            'success': True,
            'message': f'Successfully renamed "{old_name}" to "{new_name}" (fallback)',
            'operation': 'rename',
            'old_path': f'/{relative_old_path}',
            'old_name': old_name,
            'new_path': f'/{relative_new_path}',
            'new_name': new_name,
            'type': 'folder' if is_directory else 'file',
            'size': file_size,
            'renamed_at': datetime.now().isoformat(),
            'method': 'fallback'
        }
        
    except PermissionError as e:
        return create_error_response(403, f"Permission denied: {str(e)}")
    except FileExistsError as e:
        return create_error_response(409, f"Destination already exists: {str(e)}")
    except OSError as e:
        return create_error_response(500, f"Filesystem error: {str(e)}")
    except Exception as e:
        logger.error(f"Fallback rename failed: {str(e)}")
        logger.error(traceback.format_exc())
        return create_error_response(500, f"Fallback rename failed: {str(e)}")

def is_valid_filename(filename: str) -> bool:
    """Basic filename validation."""
    if not filename or filename.strip() == '':
        return False
    
    filename = filename.strip()
    
    # Check for directory references
    if filename in ['.', '..']:
        return False
    
    # Check for invalid characters
    invalid_chars = '<>:"/\\|?*'
    if any(char in filename for char in invalid_chars):
        return False
    
    # Check for control characters
    if any(ord(char) < 32 for char in filename):
        return False
    
    # Check length
    if len(filename.encode('utf-8')) > 255:
        return False
    
    return True

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response."""
    logger.error(f"ERROR {status_code}: {message}")
    return {
        'success': False,
        'error': message,
        'status_code': status_code,
        'operation': 'rename',
        'timestamp': datetime.now().isoformat()
    }

def handle_search(args):
    """Handle search operations synchronously."""
    if search_module and hasattr(search_module, 'main'):
        try:
            logger.info(f"Executing search with args: {args}")
            # Call the search module's main function
            if asyncio.iscoroutinefunction(search_module.main):
                # If it's async, run it in an event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(search_module.main(args))
                finally:
                    loop.close()
            else:
                # If it's sync, just call it
                result = search_module.main(args)
            
            logger.info(f"Search completed successfully")
            return result
        except Exception as e:
            logger.error(f"Search operation failed: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "results": []
            }
    else:
        # Fallback: simple file listing if search module not available
        logger.warning("Search module not available, using fallback")
        return fallback_search(args)

def handle_delete(args):
    """Handle delete operations synchronously."""
    if delete_module and hasattr(delete_module, 'main'):
        try:
            logger.info(f"Executing delete with args: {args}")
            if asyncio.iscoroutinefunction(delete_module.main):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(delete_module.main(args))
                finally:
                    loop.close()
            else:
                result = delete_module.main(args)
            return result
        except Exception as e:
            logger.error(f"Delete operation failed: {str(e)}")
            return {
                "success": False,
                "error": f"Delete failed: {str(e)}"
            }
    else:
        return {
            "success": False,
            "error": "Delete module not available"
        }

def handle_download(args):
    """Handle download operations synchronously."""
    if download_module and hasattr(download_module, 'main'):
        try:
            logger.info(f"Executing download with args: {args}")
            if asyncio.iscoroutinefunction(download_module.main):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(download_module.main(args))
                finally:
                    loop.close()
            else:
                result = download_module.main(args)
            return result
        except Exception as e:
            logger.error(f"Download operation failed: {str(e)}")
            return {
                "success": False,
                "error": f"Download failed: {str(e)}"
            }
    else:
        return {
            "success": False,
            "error": "Download module not available"
        }

def fallback_search(args):
    """Fallback search implementation when search module is not available."""
    try:
        base_directory = args.get('base_directory', '/tmp/filemanager')
        query = args.get('query', '*')
        search_path = args.get('search_path', '/')
        
        logger.info(f"Fallback search in {base_directory} for query: {query}")
        
        # Ensure base directory exists
        base_path = Path(base_directory)
        if not base_path.exists():
            logger.info(f"Creating base directory: {base_directory}")
            base_path.mkdir(parents=True, exist_ok=True)
        
        # Calculate full search path
        if search_path.startswith('/'):
            search_path = search_path[1:]
        full_path = base_path / search_path
        
        if not full_path.exists():
            full_path.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        # Simple file listing
        if full_path.exists() and full_path.is_dir():
            for item in full_path.rglob('*'):
                try:
                    relative_path = item.relative_to(base_path)
                    stat = item.stat()
                    
                    # Simple name matching
                    if query == '*' or query.lower() in item.name.lower():
                        results.append({
                            'id': str(hash(str(item))),
                            'name': item.name,
                            'path': f'/{relative_path}',
                            'type': 'folder' if item.is_dir() else 'file',
                            'size': stat.st_size if item.is_file() else None,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                except Exception as e:
                    logger.warning(f"Error processing {item}: {e}")
                    continue
        
        logger.info(f"Fallback search found {len(results)} results")
        
        return {
            "success": True,
            "results": results,
            "message": f"Found {len(results)} items (fallback search)",
            "total_found": len(results),
            "query": query,
            "search_path": search_path,
            "search_type": "name"
        }
        
    except Exception as e:
        logger.error(f"Fallback search failed: {str(e)}")
        return {
            "success": False,
            "results": [],
            "error": f"Fallback search failed: {str(e)}"
        }

def handle_filemanager(args):
    """Default filemanager handler."""
    return {
        "success": True,
        "message": "Filemanager is running",
        "available_operations": ["search", "delete", "rename", "download", "test"],
        "modules_loaded": {
            "search": search_module is not None,
            "delete": delete_module is not None,
            "rename": rename_module is not None,
            "download": download_module is not None
        },
        "s3_configured": bool(get_s3_parameters())
    }

def handle_test(args):
    """Test handler for debugging."""
    return {
        "success": True,
        "message": "Test endpoint working",
        "args_received": args,
        "timestamp": datetime.now().isoformat(),
        "s3_params": {k: v if 'KEY' not in k else '***' for k, v in get_s3_parameters().items()}
    }

# Operation handlers mapping
HANDLERS = {
    'search': handle_search,
    'delete': handle_delete,
    'rename': handle_rename,
    'download': handle_download,
    'filemanager': handle_filemanager,
    'test': handle_test
}

def process_request(args):
    """Process the filemanager request."""
    try:
        logger.info(f"Filemanager API called with args: {json.dumps(args, indent=2, default=str)}")
        
        # Extract operation
        operation = args.get('operation', 'search')  # Default to search for compatibility
        
        logger.info(f"Processing operation: {operation}")
        
        # Validate operation
        if operation not in HANDLERS:
            logger.error(f"Unknown operation: {operation}")
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
                "available_operations": list(HANDLERS.keys())
            }
        
        # Execute the handler
        handler = HANDLERS[operation]
        result = handler(args)
        
        logger.info(f"Operation '{operation}' completed")
        return result
        
    except Exception as e:
        error_msg = f"Unexpected error in filemanager: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "error": error_msg,
            "traceback": traceback.format_exc()
        }

# Main function with the expected signature
def main(args):
    """
    Main entry point that returns a dict with 'body' key.
    This matches the expected serverless function signature.
    """
    result = process_request(args)
    return {"body": result}

# For backwards compatibility
def search_files(args):
    """Backward compatibility wrapper."""
    return process_request(args)

def delete_files(args):
    """Backward compatibility wrapper."""
    args['operation'] = 'delete'
    return process_request(args)

def rename_file(args):
    """Backward compatibility wrapper."""
    args['operation'] = 'rename'
    return process_request(args)

def download_files(args):
    """Backward compatibility wrapper."""
    args['operation'] = 'download'
    return process_request(args)
