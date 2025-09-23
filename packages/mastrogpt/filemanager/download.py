#--kind python:default
#--web true
#--param S3_HOST $S3_HOST
#--param S3_PORT $S3_PORT
#--param S3_ACCESS_KEY $S3_ACCESS_KEY
#--param S3_SECRET_KEY $S3_SECRET_KEY
#--param S3_BUCKET_DATA $S3_BUCKET_DATA
#--param S3_API_URL $S3_API_URL
"""
download.py - External URL download handler
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import base64
import hashlib
import hmac
from datetime import datetime, timezone
import re
import os
import boto3
from typing import Dict, Any, Optional

def main(args: Dict[str, Any]) -> Dict[str, Any]:
    """Main download handler."""
    
    try:
        print("=" * 80)
        print("DOWNLOAD MODULE - START")
        print("=" * 80)
        print(f"Args received: {json.dumps(args, indent=2, default=str)}")
        
        action = args.get('action', 'download')
        operation = args.get('operation', 'download')
        
        print(f"Action: {action}, Operation: {operation}")
        
        # Ensure S3 credentials are available for all operations
        s3_config_check = {
            'S3_HOST': args.get('S3_HOST', ''),
            'S3_API_URL': args.get('S3_API_URL', ''),
            'S3_ACCESS_KEY': args.get('S3_ACCESS_KEY', os.getenv('S3_ACCESS_KEY', '')),
            'S3_SECRET_KEY': args.get('S3_SECRET_KEY', os.getenv('S3_SECRET_KEY', '')),
            'S3_BUCKET_DATA': args.get('S3_BUCKET_DATA', os.getenv('S3_BUCKET_DATA', ''))
        }
        
        print("S3 Configuration check:")
        for key, value in s3_config_check.items():
            if 'SECRET' in key:
                print(f"  {key}: {'*' * len(value) if value else '(missing)'}")
            else:
                print(f"  {key}: '{value}'")
        
        # File information
        file_info = args.get('file', {})
        if not isinstance(file_info, dict):
            return create_error_response(400, 'File parameter must be an object')
        
        file_name = file_info.get('name', '').strip()
        file_key = file_info.get('key', '').strip()  
        file_url = file_info.get('url', '').strip()
        
        print(f"File details: name='{file_name}', key='{file_key}', url='{file_url}'")
        
        if not file_name:
            return create_error_response(400, 'File name is required')
        
        # Handle different download methods
        if action == 'generate_presigned_url' and file_key:
            return handle_generate_presigned_url(args, file_key, file_name)
        elif file_key:
            return handle_s3_download(args, file_key, file_name)
        elif file_url:
            return handle_url_download(file_url, file_name)
        else:
            return create_error_response(400, 'Either file key (for S3) or URL must be provided')
            
    except Exception as e:
        print(f"ERROR in download handler: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_error_response(500, f'Internal server error: {str(e)}')

def s3client(args):
    """Create S3 client similar to display.py"""
    base = args.get("S3_API_URL") or args.get("S3_HOST")
    key = args.get("S3_ACCESS_KEY", os.getenv("S3_ACCESS_KEY"))
    sec = args.get("S3_SECRET_KEY", os.getenv("S3_SECRET_KEY"))
    bucket = args.get("S3_BUCKET_DATA", os.getenv("S3_BUCKET_DATA"))
    port = args.get("S3_PORT", "443")
    
    # Handle port in URL
    if base and not base.startswith("http"):
        protocol = "https" if port == "443" else "http"
        if port not in ["80", "443"]:
            base = f"{protocol}://{base}:{port}"
        else:
            base = f"{protocol}://{base}"
    
    client = boto3.client('s3', 
                         region_name='us-east-1', 
                         endpoint_url=base, 
                         aws_access_key_id=key, 
                         aws_secret_access_key=sec)
    return client, bucket

def list_bucket_objects_debug(client, bucket: str, prefix: str = "") -> list:
    """List objects in bucket for debugging purposes."""
    
    try:
        print(f"Listing bucket objects with prefix: '{prefix}'")
        
        # Try to list objects with different prefixes
        prefixes_to_try = [
            prefix,                    # Original prefix
            prefix.lstrip('/'),       # Remove leading slash
            prefix.split('/')[0] if '/' in prefix else prefix,  # First part only
            "",                       # List all objects (first 20)
        ]
        
        found_objects = []
        
        for search_prefix in prefixes_to_try:
            try:
                print(f"  Trying prefix: '{search_prefix}'")
                response = client.list_objects_v2(
                    Bucket=bucket, 
                    Prefix=search_prefix, 
                    MaxKeys=20
                )
                
                if 'Contents' in response:
                    objects = [obj['Key'] for obj in response['Contents']]
                    print(f"    Found {len(objects)} objects")
                    for obj_key in objects:
                        print(f"      - {obj_key}")
                        if obj_key not in found_objects:
                            found_objects.append(obj_key)
                else:
                    print(f"    No objects found with prefix '{search_prefix}'")
            except Exception as e:
                print(f"    Error listing with prefix '{search_prefix}': {e}")
        
        return found_objects
        
    except Exception as e:
        print(f"Error listing bucket objects: {e}")
        return []

def find_matching_keys(client, bucket: str, search_key: str) -> list:
    """Find keys that might match the requested key using various strategies."""
    
    print(f"Searching for keys matching: '{search_key}'")
    
    matching_keys = []
    
    # Strategy 1: Try exact variations
    key_variations = [
        search_key,
        search_key.lstrip('/'),
        search_key.rstrip('/'),
        search_key.replace('//', '/'),
        search_key.strip(),
    ]
    
    # Strategy 2: Try URL decoded version
    try:
        decoded_key = urllib.parse.unquote(search_key)
        if decoded_key != search_key:
            key_variations.append(decoded_key)
            print(f"  Added URL decoded version: '{decoded_key}'")
    except:
        pass
    
    # Strategy 3: Try with common upload prefixes
    filename = search_key.split('/')[-1] if '/' in search_key else search_key
    print(f"  Extracted filename: '{filename}'")
    
    common_prefixes = [
        f"uploads/{filename}",
        f"images/{filename}",
        f"files/{filename}",
        f"media/{filename}",
        f"public/{filename}",
        f"tmp/{filename}",
        f"data/{filename}",
        f"assets/{filename}",
        filename  # Just the filename
    ]
    key_variations.extend(common_prefixes)
    
    # Strategy 4: Try with timestamp or hash prefixes (common in uploads)
    import re
    # Look for patterns like: "20240801_image.jpg", "abc123_image.jpg", etc.
    timestamp_variations = [
        f"upload_{filename}",
        f"file_{filename}",
        f"img_{filename}",
    ]
    key_variations.extend(timestamp_variations)
    
    # Remove duplicates
    unique_variations = []
    seen = set()
    for var in key_variations:
        if var and var not in seen:
            seen.add(var)
            unique_variations.append(var)
    
    print(f"Trying {len(unique_variations)} key variations:")
    for i, var in enumerate(unique_variations):
        print(f"  {i+1}. '{var}'")
    
    # Test each variation
    for key_var in unique_variations:
        try:
            client.head_object(Bucket=bucket, Key=key_var)
            print(f"  ✓ Found: '{key_var}'")
            matching_keys.append(key_var)
        except Exception as e:
            # Don't print every miss, just the important ones
            if key_var == search_key:
                print(f"  ✗ Original key not found: '{key_var}' - {e}")
    
    # Strategy 5: Aggressive search - list ALL objects and find matches
    print(f"Found {len(matching_keys)} exact matches. Scanning all bucket objects...")
    
    try:
        # List ALL objects in bucket (up to 1000)
        response = client.list_objects_v2(Bucket=bucket, MaxKeys=1000)
        if 'Contents' in response:
            all_objects = [obj['Key'] for obj in response['Contents']]
            print(f"Bucket contains {len(all_objects)} total objects")
            
            # Show first 10 objects for debugging
            print("First 10 objects in bucket:")
            for i, obj_key in enumerate(all_objects[:10]):
                print(f"  {i+1}. '{obj_key}'")
            
            # Extract just the filename from search key for matching
            search_filename = search_key.split('/')[-1] if '/' in search_key else search_key
            search_name_lower = search_filename.lower()
            
            # Remove file extension for looser matching
            search_base = search_filename.rsplit('.', 1)[0] if '.' in search_filename else search_filename
            search_base_lower = search_base.lower()
            
            print(f"Searching for filename: '{search_filename}' or base: '{search_base}'")
            
            for obj_key in all_objects:
                obj_filename = obj_key.split('/')[-1]
                obj_filename_lower = obj_filename.lower()
                obj_base = obj_filename.rsplit('.', 1)[0] if '.' in obj_filename else obj_filename
                obj_base_lower = obj_base.lower()
                
                # Multiple matching strategies
                matches = False
                match_reason = None
                
                # Exact filename match
                if search_filename.lower() == obj_filename_lower:
                    matches = True
                    match_reason = "exact filename"
                
                # Base name match (without extension)
                elif search_base_lower == obj_base_lower:
                    matches = True
                    match_reason = "base filename"
                
                # Contains search term
                elif search_name_lower in obj_filename_lower:
                    matches = True
                    match_reason = "filename contains search"
                
                # Search term contains object name
                elif obj_filename_lower in search_name_lower:
                    matches = True
                    match_reason = "search contains filename"
                
                # Full path matching
                elif search_key.lower() in obj_key.lower():
                    matches = True
                    match_reason = "path contains search"
                
                if matches and obj_key not in matching_keys:
                    print(f"  ~ Found match: '{obj_key}' (reason: {match_reason})")
                    matching_keys.append(obj_key)
        else:
            print("Bucket is empty or no objects found")
            
    except Exception as e:
        print(f"Error scanning bucket objects: {e}")
    
    print(f"Total matches found: {len(matching_keys)}")
    return matching_keys

def handle_s3_download(args: Dict[str, Any], file_key: str, file_name: str) -> Dict[str, Any]:
    """Download file from S3 using boto3 with enhanced key detection"""
    
    try:
        client, bucket = s3client(args)
        
        print(f"S3 Download Debug:")
        print(f"  Bucket: {bucket}")
        print(f"  Original key: '{file_key}'")
        print(f"  Key length: {len(file_key)}")
        print(f"  Key bytes: {file_key.encode('utf-8')}")
        
        # First, try to find matching keys using comprehensive search
        matching_keys = find_matching_keys(client, bucket, file_key)
        
        if not matching_keys:
            print("No matching keys found. Listing recent uploads...")
            # List recent objects to help debug
            all_objects = list_bucket_objects_debug(client, bucket, "")
            
            return create_error_response(404, 
                f'Object not found with key "{file_key}". '
                f'Found {len(all_objects)} objects in bucket. '
                f'Recent objects: {all_objects[:5] if all_objects else "none"}'
            )
        
        print(f"Found {len(matching_keys)} potential matches: {matching_keys}")
        
        # Try each matching key
        last_error = None
        for key_var in matching_keys:
            print(f"\nAttempting download with key: '{key_var}'")
            
            try:
                # Get the object
                response = client.get_object(Bucket=bucket, Key=key_var)
                file_content = response['Body'].read()
                
                content_length = len(file_content)
                print(f"  SUCCESS: Downloaded {content_length} bytes with key '{key_var}'")
                
                if content_length == 0:
                    print(f"  WARNING: File is empty")
                    last_error = create_error_response(400, 'Downloaded file is empty')
                    continue
                
                # Check file size limit (100MB)
                max_size = 100 * 1024 * 1024
                if content_length > max_size:
                    return create_error_response(400, f'File too large: {content_length} bytes')
                
                file_base64 = base64.b64encode(file_content).decode('utf-8')
                
                return {
                    'success': True,
                    'file': {
                        'name': file_name,
                        'size': content_length,
                        'base64': file_base64,
                        'content_type': response.get('ContentType', 'application/octet-stream'),
                        'key': key_var,
                        'original_key': file_key,
                        'matched_key': key_var if key_var != file_key else None
                    },
                    'source': 's3'
                }
                
            except Exception as e:
                print(f"  Failed with key '{key_var}': {e}")
                last_error = create_error_response(500, f'S3 error with key "{key_var}": {str(e)}')
                continue
        
        # All matching keys failed
        return last_error or create_error_response(404, f'Could not download any matching objects for key: "{file_key}"')
        
    except Exception as e:
        print(f"Critical S3 download error: {e}")
        import traceback
        traceback.print_exc()
        return create_error_response(500, f'S3 download error: {str(e)}')

def handle_generate_presigned_url(args: Dict[str, Any], file_key: str, file_name: str) -> Dict[str, Any]:
    """Generate presigned URL using boto3"""
    
    try:
        print(f"Generating presigned URL for key: '{file_key}'")
        
        # Check S3 configuration
        s3_host = args.get("S3_HOST") or args.get("S3_API_URL")
        s3_access_key = args.get("S3_ACCESS_KEY", os.getenv("S3_ACCESS_KEY"))
        s3_secret_key = args.get("S3_SECRET_KEY", os.getenv("S3_SECRET_KEY"))
        s3_bucket = args.get("S3_BUCKET_DATA", os.getenv("S3_BUCKET_DATA"))
        
        print(f"S3 Config check:")
        print(f"  Host: {s3_host}")
        print(f"  Access Key: {'*' * len(s3_access_key) if s3_access_key else '(missing)'}")
        print(f"  Secret Key: {'*' * len(s3_secret_key) if s3_secret_key else '(missing)'}")
        print(f"  Bucket: {s3_bucket}")
        
        missing_config = []
        if not s3_host:
            missing_config.append("S3_HOST/S3_API_URL")
        if not s3_access_key:
            missing_config.append("S3_ACCESS_KEY")
        if not s3_secret_key:
            missing_config.append("S3_SECRET_KEY")
        if not s3_bucket:
            missing_config.append("S3_BUCKET_DATA")
            
        if missing_config:
            error_msg = f'S3 configuration incomplete. Missing: {", ".join(missing_config)}'
            print(f"ERROR: {error_msg}")
            return create_error_response(400, error_msg)
        
        client, bucket = s3client(args)
        expires_in = args.get('expires_in', 3600)
        
        if not isinstance(expires_in, int) or expires_in <= 0 or expires_in > 604800:
            expires_in = 3600
        
        print(f"Generating URL with expires_in: {expires_in}")
        
        presigned_url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': file_key},
            ExpiresIn=expires_in
        )
        
        print(f"Successfully generated presigned URL")
        
        return {
            'success': True,
            'presigned_url': presigned_url,
            'expires_in': expires_in,
            'file_key': file_key,
            'file_name': file_name
        }
        
    except Exception as e:
        print(f"Presigned URL generation error: {e}")
        import traceback
        traceback.print_exc()
        return create_error_response(500, f'Presigned URL generation error: {str(e)}')

def handle_url_download(url: str, file_name: str) -> Dict[str, Any]:
    """Download from external URL"""
    
    print(f"Downloading from URL: {url}")
    
    if not is_valid_url(url):
        return create_error_response(400, 'Invalid URL format')
    
    try:
        headers = {
            'User-Agent': 'File-Downloader/1.0',
            'Accept': '*/*'
        }
        
        request = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"Response status: {response.status}")
            
            if response.status == 200:
                file_content = response.read()
                content_length = len(file_content)
                
                print(f"Downloaded {content_length} bytes from URL")
                
                if content_length == 0:
                    return create_error_response(400, 'Downloaded file is empty')
                
                # Check file size limit (100MB)
                max_size = 100 * 1024 * 1024
                if content_length > max_size:
                    return create_error_response(400, f'File too large: {content_length} bytes')
                
                file_base64 = base64.b64encode(file_content).decode('utf-8')
                
                return {
                    'success': True,
                    'file': {
                        'name': file_name,
                        'size': content_length,
                        'base64': file_base64,
                        'content_type': response.headers.get('content-type', 'application/octet-stream'),
                        'url': url
                    },
                    'source': 'external_url'
                }
            else:
                return create_error_response(response.status, f'HTTP error: {response.status}')
    
    except urllib.error.HTTPError as e:
        error_msg = f'HTTP error {e.code}'
        try:
            error_body = e.read().decode('utf-8')[:200]
            error_msg += f' - {error_body}'
        except:
            pass
        return create_error_response(e.code, error_msg)
    
    except urllib.error.URLError as e:
        return create_error_response(500, f'URL error: {str(e)}')
    
    except Exception as e:
        print(f"Download exception: {e}")
        return create_error_response(500, f'Download error: {str(e)}')

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response"""
    print(f"ERROR {status_code}: {message}")
    return {
        'error': message,
        'success': False,
        'status_code': status_code
    }

def is_valid_url(url: str) -> bool:
    """Validate URL format"""
    if not url:
        return False
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None

def is_valid_filename(filename: str) -> bool:
    """Validate filename"""
    if not filename or len(filename) > 255:
        return False
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    return not any(char in filename for char in invalid_chars)

# Example usage functions
def download_example():
    """Example of how to use the download function"""
    
    # Example 1: Download from external URL
    args1 = {
        'action': 'download',
        'file': {
            'name': 'example.pdf',
            'url': 'https://example.com/files/document.pdf'
        }
    }
    
    # Example 2: Download from S3
    args2 = {
        'action': 'download',
        'file': {
            'name': 'data.csv',
            'key': 'uploads/data.csv'
        },
        'S3_HOST': 's3.amazonaws.com',
        'S3_ACCESS_KEY': 'your-access-key',
        'S3_SECRET_KEY': 'your-secret-key',
        'S3_BUCKET_DATA': 'your-bucket'
    }
    
    # Example 3: Generate presigned URL
    args3 = {
        'action': 'generate_presigned_url',
        'file': {
            'name': 'image.jpg',
            'key': 'images/photo.jpg'
        },
        'expires_in': 3600,
        'S3_HOST': 's3.amazonaws.com',
        'S3_ACCESS_KEY': 'your-access-key',
        'S3_SECRET_KEY': 'your-secret-key',
        'S3_BUCKET_DATA': 'your-bucket'
    }
    
    return [args1, args2, args3]