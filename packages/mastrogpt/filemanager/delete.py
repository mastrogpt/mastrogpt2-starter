#--kind python:default
#--web true
#--param S3_HOST $S3_HOST
#--param S3_PORT $S3_PORT
#--param S3_ACCESS_KEY $S3_ACCESS_KEY
#--param S3_SECRET_KEY $S3_SECRET_KEY
#--param S3_BUCKET_DATA $S3_BUCKET_DATA
#--param S3_API_URL $S3_API_URL
"""
API Path: api/my/filemanagement/delete
This action handles deleting files and folders from S3 storage.
"""
import os
import json
import boto3
from datetime import datetime
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(args):
    """Main entry point for S3 delete operations."""
    
    print("=" * 80)
    print("S3 DELETE: Starting...")
    print("=" * 80)
    print(f"S3 DELETE: Args = {json.dumps(args, indent=2, default=str)}")
    
    # Get parameters
    paths = args.get('paths', [])
    force = args.get('force', False)
    
    print(f"S3 DELETE: paths={paths}")
    print(f"S3 DELETE: force={force}")
    
    # Validate parameters
    if not paths:
        print("S3 DELETE: ERROR - No paths provided")
        return {"success": False, "error": "paths parameter is required"}
    
    if isinstance(paths, str):
        paths = [paths]
    elif not isinstance(paths, list):
        print("S3 DELETE: ERROR - Invalid paths format")
        return {"success": False, "error": "paths must be an array or string"}
    
    try:
        # Get S3 client and bucket
        client, bucket = s3client(args)
        print(f"S3 DELETE: Using bucket '{bucket}'")
        
        deleted_items = []
        failed_items = []
        
        # Process each path
        for path in paths:
            try:
                print(f"\nS3 DELETE: Processing path: '{path}'")
                
                # Clean the path to use as S3 key
                s3_key = path.lstrip('/')
                print(f"S3 DELETE: S3 key: '{s3_key}'")
                
                # Check if the object exists in S3
                print("S3 DELETE: Checking if object exists...")
                try:
                    response = client.head_object(Bucket=bucket, Key=s3_key)
                    print(f"S3 DELETE: ✅ Object exists - Size: {response.get('ContentLength', 0)} bytes")
                    object_exists = True
                    content_type = response.get('ContentType', 'application/octet-stream')
                except Exception as e:
                    print(f"S3 DELETE: ❌ Object does not exist: {e}")
                    
                    # Try to find similar objects for debugging
                    print("S3 DELETE: Searching for similar objects...")
                    try:
                        # List objects with the same prefix (folder)
                        prefix = '/'.join(s3_key.split('/')[:-1]) if '/' in s3_key else ''
                        objects = client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=20)
                        
                        if 'Contents' in objects:
                            found_keys = [obj['Key'] for obj in objects['Contents']]
                            print(f"S3 DELETE: Found objects with prefix '{prefix}': {found_keys}")
                            
                            # Look for exact match (case insensitive)
                            s3_key_lower = s3_key.lower()
                            matches = [k for k in found_keys if k.lower() == s3_key_lower]
                            
                            if matches:
                                actual_key = matches[0]
                                print(f"S3 DELETE: Found case-sensitive match: '{actual_key}'")
                                s3_key = actual_key
                                object_exists = True
                            else:
                                # Look for filename matches
                                filename = s3_key.split('/')[-1].lower()
                                filename_matches = [k for k in found_keys if k.split('/')[-1].lower() == filename]
                                
                                if filename_matches:
                                    print(f"S3 DELETE: Found filename matches: {filename_matches}")
                                    # Use the first match
                                    s3_key = filename_matches[0]
                                    print(f"S3 DELETE: Using matched key: '{s3_key}'")
                                    object_exists = True
                                else:
                                    object_exists = False
                        else:
                            print("S3 DELETE: No objects found in bucket with that prefix")
                            object_exists = False
                            
                    except Exception as search_error:
                        print(f"S3 DELETE: Could not search for objects: {search_error}")
                        object_exists = False
                
                if not object_exists:
                    failed_items.append({
                        'success': False,
                        'path': path,
                        'error': 'OBJECT_NOT_FOUND',
                        'message': f'Object not found in S3: {path}'
                    })
                    continue
                
                # Perform the delete operation
                print(f"S3 DELETE: Deleting object with key: '{s3_key}'")
                try:
                    client.delete_object(Bucket=bucket, Key=s3_key)
                    print("S3 DELETE: ✅ Delete successful")
                    
                    # Verify deletion
                    try:
                        client.head_object(Bucket=bucket, Key=s3_key)
                        print("S3 DELETE: ❌ Object still exists after delete")
                        failed_items.append({
                            'success': False,
                            'path': path,
                            'error': 'DELETE_VERIFICATION_FAILED',
                            'message': f'Object still exists after delete attempt: {path}'
                        })
                    except:
                        print("S3 DELETE: ✅ Verified - object no longer exists")
                        
                        # Extract filename for response
                        filename = s3_key.split('/')[-1] if '/' in s3_key else s3_key
                        
                        deleted_items.append({
                            'success': True,
                            'path': path,
                            'name': filename,
                            'type': 'file',  # S3 objects are always files
                            's3_key': s3_key,
                            'bucket': bucket,
                            'message': f'Successfully deleted "{filename}" from S3'
                        })
                        
                except Exception as delete_error:
                    print(f"S3 DELETE: ❌ Delete failed: {delete_error}")
                    failed_items.append({
                        'success': False,
                        'path': path,
                        'error': 'S3_DELETE_FAILED',
                        'message': f'S3 delete failed: {str(delete_error)}'
                    })
                
            except Exception as e:
                print(f"S3 DELETE: ❌ Error processing path '{path}': {e}")
                failed_items.append({
                    'success': False,
                    'path': path,
                    'error': 'PROCESSING_ERROR',
                    'message': f'Error processing deletion: {str(e)}'
                })
        
        # Calculate results
        total_items = len(paths)
        successful_deletions = len(deleted_items)
        
        if successful_deletions == total_items:
            message = f'Successfully deleted {successful_deletions} item(s) from S3'
            success = True
        elif successful_deletions > 0:
            message = f'Deleted {successful_deletions} of {total_items} items from S3. {len(failed_items)} failed.'
            success = True  # Partial success
        else:
            message = f'Failed to delete all {total_items} items from S3'
            success = False
        
        result = {
            'success': success,
            'message': message,
            'deleted_items': deleted_items,
            'failed_items': failed_items,
            'total_items': total_items,
            'successful_deletions': successful_deletions,
            'deleted_count': successful_deletions,
            'bucket': bucket,
            'operation': 's3_delete',
            'timestamp': datetime.now().isoformat()
        }
        
        print("=" * 80)
        print("S3 DELETE: FINAL RESULT")
        print("=" * 80)
        print(json.dumps(result, indent=2, default=str))
        
        return result
        
    except Exception as e:
        print(f"S3 DELETE: ❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': 'S3_DELETE_ERROR',
            'message': f'S3 delete operation failed: {str(e)}'
        }

def s3client(args):
    """Create S3 client - same as download.py"""
    base = args.get("S3_API_URL") or args.get("S3_HOST")
    key = args.get("S3_ACCESS_KEY", os.environ.get("S3_ACCESS_KEY"))
    sec = args.get("S3_SECRET_KEY", os.environ.get("S3_SECRET_KEY"))
    bucket = args.get("S3_BUCKET_DATA", os.environ.get("S3_BUCKET_DATA"))
    port = args.get("S3_PORT", "443")
    
    print(f"S3 CONFIG:")
    print(f"  Host/URL: {base}")
    print(f"  Port: {port}")
    print(f"  Access Key: {'*' * len(key) if key else '(missing)'}")
    print(f"  Secret Key: {'*' * len(sec) if sec else '(missing)'}")
    print(f"  Bucket: {bucket}")
    
    # Handle port in URL
    if base and not base.startswith("http"):
        protocol = "https" if port == "443" else "http"
        if port not in ["80", "443"]:
            base = f"{protocol}://{base}:{port}"
        else:
            base = f"{protocol}://{base}"
    
    if not key or not sec or not bucket:
        raise Exception(f"Missing S3 credentials: key={bool(key)}, secret={bool(sec)}, bucket={bool(bucket)}")
    
    client = boto3.client('s3', 
                         region_name='us-east-1', 
                         endpoint_url=base, 
                         aws_access_key_id=key, 
                         aws_secret_access_key=sec)
    
    return client, bucket

# Backward compatibility wrapper
def main_handler(args):
    """Backward compatibility wrapper."""
    return main(args)

# Test function for S3 delete
def test_s3_delete():
    """Test the S3 delete function."""
    
    test_args = {
        'paths': ['/test-file.txt'],
        'force': True,
        # S3 credentials would come from environment
    }
    
    print("Testing S3 delete...")
    result = main(test_args)
    print(f"Test result: {json.dumps(result, indent=2, default=str)}")
    return result

if __name__ == "__main__":
    print("S3 Delete module loaded")
    # Uncomment to test: test_s3_delete()