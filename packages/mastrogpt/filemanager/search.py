#--kind python:default
#--web true
#--param S3_HOST $S3_HOST
#--param S3_PORT $S3_PORT
#--param S3_ACCESS_KEY $S3_ACCESS_KEY
#--param S3_SECRET_KEY $S3_SECRET_KEY
#--param S3_BUCKET_DATA $S3_BUCKET_DATA

"""
API Path: api/my/filemanagement/search
Enhanced file and folder search functionality with S3 support,
improved performance, security, and features.
FIXED: Now shows ALL files in bucket without limits.
"""
import os
import json
import asyncio
import fnmatch
import mimetypes
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10MB max for content search
CHUNK_SIZE = 8192  # For reading files in chunks
TEXT_EXTENSIONS = {'.txt', '.md', '.py', '.js', '.jsx', '.ts', '.tsx', '.java', 
                   '.c', '.cpp', '.h', '.hpp', '.cs', '.php', '.rb', '.go',
                   '.rs', '.swift', '.kt', '.scala', '.r', '.m', '.sql',
                   '.sh', '.bash', '.ps1', '.xml', '.json', '.yaml', '.yml',
                   '.toml', '.ini', '.cfg', '.conf', '.log', '.csv', '.html',
                   '.htm', '.css', '.scss', '.sass', '.less'}

@dataclass
class SearchResult:
    """Data class for search results."""
    id: str
    name: str
    path: str
    type: str
    match_type: str
    size: Optional[int]
    modified: str
    parent_path: str
    extension: Optional[str] = None
    preview: Optional[str] = None
    match_count: Optional[int] = None
    permissions: Optional[str] = None
    source: str = 'local'  # 'local' or 's3'
    s3_url: Optional[str] = None
    s3_key: Optional[str] = None

class S3SearchManager:
    """Handles S3 file searching and operations."""
    
    def __init__(self, s3_config: Dict[str, str]):
        self.s3_config = s3_config
        self.s3_client = None
        self._initialize_s3_client()
    
    def _initialize_s3_client(self):
        """Initialize S3 client with configuration."""
        try:
            if not all([
                self.s3_config.get('S3_HOST'),
                self.s3_config.get('S3_ACCESS_KEY'),
                self.s3_config.get('S3_SECRET_KEY'),
                self.s3_config.get('S3_BUCKET_DATA')
            ]):
                logger.warning("S3 configuration incomplete, S3 search will be disabled")
                return
            
            # Parse S3 endpoint
            s3_host = self.s3_config['S3_HOST']
            s3_port = self.s3_config.get('S3_PORT', '443')
            
            # Handle different S3 endpoint formats
            if s3_host.startswith('http://') or s3_host.startswith('https://'):
                endpoint_url = s3_host
            elif s3_port != '443':
                endpoint_url = f"http://{s3_host}:{s3_port}"
                use_ssl = False
            else:
                endpoint_url = f"https://{s3_host}"
                use_ssl = True
            
            logger.info(f"Initializing S3 client with endpoint: {endpoint_url}")
            
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=self.s3_config['S3_ACCESS_KEY'],
                aws_secret_access_key=self.s3_config['S3_SECRET_KEY'],
                use_ssl=use_ssl if 'use_ssl' in locals() else True,
                verify=False  # For self-signed certificates
            )
            
            # Test connection
            bucket = self.s3_config['S3_BUCKET_DATA']
            self.s3_client.head_bucket(Bucket=bucket)
            logger.info(f"S3 client initialized successfully for bucket: {bucket}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"S3 bucket not found: {self.s3_config.get('S3_BUCKET_DATA')}")
            elif error_code == '403':
                logger.error("S3 access denied - check credentials")
            else:
                logger.error(f"S3 client error: {error_code} - {str(e)}")
            self.s3_client = None
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            self.s3_client = None
    
    async def list_all_s3_objects(self) -> List[SearchResult]:
        """List ALL objects in S3 bucket - no limits, no filters."""
        if not self.s3_client:
            logger.warning("S3 client not available, skipping S3 listing")
            return []
        
        try:
            bucket = self.s3_config['S3_BUCKET_DATA']
            results = []
            objects_scanned = 0
            
            logger.info(f"Starting COMPLETE S3 bucket scan: '{bucket}'")
            
            # Use paginator to scan ENTIRE bucket - no MaxKeys limit
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket)
            
            for page_num, page in enumerate(page_iterator, 1):
                if 'Contents' not in page:
                    logger.info(f"Page {page_num}: No objects found")
                    continue
                
                page_objects = len(page['Contents'])
                logger.info(f"Page {page_num}: Processing {page_objects} objects")
                
                for obj in page['Contents']:
                    objects_scanned += 1
                    
                    # Extract object info
                    key = obj['Key']
                    name = os.path.basename(key) or key
                    size = obj['Size']
                    modified = obj['LastModified']
                    
                    # Skip directories (keys ending with /) but include everything else
                    if key.endswith('/') and size == 0:
                        continue
                    
                    result = SearchResult(
                        id=f"s3_{abs(hash(key))}",
                        name=name,
                        path=f"/{key}",
                        type='file',
                        match_type='list_all',
                        size=size,
                        modified=modified.isoformat(),
                        parent_path=f"/{os.path.dirname(key)}" if os.path.dirname(key) else '/',
                        extension=os.path.splitext(name)[1].lower() if '.' in name else None,
                        source='s3',
                        s3_url=f"s3://{bucket}/{key}",
                        s3_key=key
                    )
                    
                    results.append(result)
                    
                    # Progress logging for large buckets
                    if objects_scanned % 1000 == 0:
                        logger.info(f"Processed {objects_scanned} objects so far...")
            
            logger.info(f"COMPLETE S3 scan finished: found {len(results)} files from {objects_scanned} total objects")
            return results
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"S3 complete listing error ({error_code}): {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected S3 complete listing error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def search_s3_objects(
        self,
        query: str,
        search_type: str = 'name',
        case_sensitive: bool = False,
        max_results: int = None,  # REMOVED LIMIT - can be None for unlimited
        file_extensions: List[str] = None,
        regex_search: bool = False,
        include_preview: bool = False,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        modified_after: Optional[datetime] = None,
        modified_before: Optional[datetime] = None
    ) -> List[SearchResult]:
        """Search S3 objects based on criteria - UNLIMITED RESULTS."""
        if not self.s3_client:
            logger.warning("S3 client not available, skipping S3 search")
            return []
        
        # Special case: if query is '*' or empty, list all files
        if query == '*' or query.strip() == '':
            logger.info("Wildcard or empty query detected - listing ALL files")
            return await self.list_all_s3_objects()
        
        try:
            bucket = self.s3_config['S3_BUCKET_DATA']
            results = []
            objects_scanned = 0
            
            logger.info(f"Starting S3 search in bucket '{bucket}' for query '{query}' (unlimited results)")
            
            # List all objects in bucket - NO LIMITS
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket)
            
            search_query = query if case_sensitive else query.lower()
            
            # Compile regex if needed
            pattern = None
            if regex_search:
                try:
                    pattern = re.compile(query, re.IGNORECASE if not case_sensitive else 0)
                except re.error as e:
                    logger.error(f"Invalid regex pattern: {str(e)}")
                    return results
            
            for page in page_iterator:
                if 'Contents' not in page:
                    logger.info("No objects found in S3 bucket")
                    continue
                
                for obj in page['Contents']:
                    objects_scanned += 1
                    
                    # REMOVED: if len(results) >= max_results: break
                    # Now we process ALL objects regardless of current result count
                    
                    # Extract object info
                    key = obj['Key']
                    name = os.path.basename(key) or key
                    size = obj['Size']
                    modified = obj['LastModified']
                    
                    # Skip directories (keys ending with /)
                    if key.endswith('/') and size == 0:
                        continue
                    
                    # Apply size filters
                    if min_size and size < min_size:
                        continue
                    if max_size and size > max_size:
                        continue
                    
                    # Apply date filters
                    if modified_after and modified < modified_after:
                        continue
                    if modified_before and modified > modified_before:
                        continue
                    
                    # Apply extension filter
                    if file_extensions:
                        ext = os.path.splitext(name)[1].lower()
                        if ext not in file_extensions:
                            continue
                    
                    # Check name match
                    name_matched = False
                    if search_type in ['name', 'both']:
                        if self._matches_s3(name, search_query, pattern, case_sensitive):
                            name_matched = True
                    
                    # Check content match if needed
                    content_matched = False
                    match_info = None
                    if search_type in ['content', 'both'] and not name_matched:
                        if await self._should_search_s3_content(key, size):
                            match_info = await self._search_s3_content(
                                bucket, key, search_query, pattern, case_sensitive
                            )
                            if match_info:
                                content_matched = True
                    
                    # Create result if matched
                    if name_matched or content_matched:
                        match_type = 'name' if name_matched else 'content'
                        
                        result = SearchResult(
                            id=f"s3_{abs(hash(key))}",
                            name=name,
                            path=f"/{key}",
                            type='file',
                            match_type=match_type,
                            size=size,
                            modified=modified.isoformat(),
                            parent_path=f"/{os.path.dirname(key)}" if os.path.dirname(key) else '/',
                            extension=os.path.splitext(name)[1].lower() if '.' in name else None,
                            source='s3',
                            s3_url=f"s3://{bucket}/{key}",
                            s3_key=key
                        )
                        
                        # Add match info if available
                        if match_info:
                            result.match_count, result.preview = match_info
                        elif include_preview and name_matched:
                            # Get preview for name matches
                            result.preview = await self._get_s3_preview(bucket, key)
                        
                        results.append(result)
                
                # REMOVED: if len(results) >= max_results: break
                # Now we scan ALL pages regardless of result count
                
                # Progress logging
                if objects_scanned % 1000 == 0:
                    logger.info(f"Scanned {objects_scanned} objects, found {len(results)} matches so far...")
            
            logger.info(f"S3 search complete: scanned {objects_scanned} objects, found {len(results)} matches (unlimited)")
            return results
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"S3 search error ({error_code}): {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected S3 search error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _matches_s3(self, text: str, query: str, pattern: Optional[re.Pattern], 
                    case_sensitive: bool) -> bool:
        """Check if S3 object name matches the search criteria."""
        # Special case: if query is '*', match everything
        if query == '*':
            return True
            
        if pattern:
            return bool(pattern.search(text))
        
        search_text = text if case_sensitive else text.lower()
        
        # Support wildcards
        if '*' in query or '?' in query:
            return fnmatch.fnmatch(search_text, query)
        
        return query in search_text
    
    async def _should_search_s3_content(self, key: str, size: int) -> bool:
        """Determine if S3 object content should be searched."""
        # Check file size
        if size > MAX_CONTENT_SIZE:
            return False
        
        # Check if it's a known text file
        ext = os.path.splitext(key)[1].lower()
        if ext in TEXT_EXTENSIONS:
            return True
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(key)
        if mime_type and mime_type.startswith('text/'):
            return True
        
        return False
    
    async def _search_s3_content(
        self,
        bucket: str,
        key: str,
        query: str,
        pattern: Optional[re.Pattern],
        case_sensitive: bool
    ) -> Optional[Tuple[int, str]]:
        """Search S3 object content."""
        try:
            # Download object content
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content_bytes = response['Body'].read()
            
            # Try to decode content
            content = None
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    content = content_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if not content:
                return None
            
            # Search content
            if pattern:
                matches = list(pattern.finditer(content))
                if matches:
                    first_match = matches[0]
                    preview = self._extract_preview(
                        content, first_match.start(), len(query)
                    )
                    return len(matches), preview
            else:
                search_content = content if case_sensitive else content.lower()
                if query in search_content:
                    count = search_content.count(query)
                    idx = search_content.find(query)
                    preview = self._extract_preview(content, idx, len(query))
                    return count, preview
            
            return None
            
        except Exception as e:
            logger.debug(f"Error searching S3 content {key}: {str(e)}")
            return None
    
    async def _get_s3_preview(self, bucket: str, key: str, max_chars: int = 200) -> Optional[str]:
        """Get a preview of S3 object content."""
        try:
            # Get partial content for preview
            response = self.s3_client.get_object(
                Bucket=bucket, 
                Key=key,
                Range=f'bytes=0-{max_chars * 2}'  # Get a bit more to account for encoding
            )
            content_bytes = response['Body'].read()
            
            # Decode content
            try:
                content = content_bytes.decode('utf-8', errors='ignore')
            except:
                return None
            
            # Clean up preview
            preview = content[:max_chars]
            preview = preview.replace('\n', ' ').replace('\r', ' ')
            preview = ' '.join(preview.split())
            
            if len(content) > max_chars:
                preview += '...'
            
            return preview
            
        except Exception:
            return None
    
    def _extract_preview(self, content: str, match_pos: int, match_len: int, 
                        context_chars: int = 50) -> str:
        """Extract preview text around match."""
        start = max(0, match_pos - context_chars)
        end = min(len(content), match_pos + match_len + context_chars)
        
        preview = content[start:end]
        
        # Clean up preview
        preview = preview.replace('\n', ' ').replace('\r', ' ')
        preview = ' '.join(preview.split())
        
        # Add ellipsis if truncated
        if start > 0:
            preview = '...' + preview
        if end < len(content):
            preview = preview + '...'
        
        return preview

class FileSearcher:
    """Enhanced file searcher with local and S3 support."""
    
    def __init__(self, base_directory: str, s3_config: Dict[str, str], max_workers: int = 4):
        self.base_path = Path(base_directory).resolve()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.s3_manager = S3SearchManager(s3_config)
        
    async def search(
        self,
        query: str = '*',  # Default to show all files
        search_path: str = '/',
        search_type: str = 'name',
        include_folders: bool = True,
        case_sensitive: bool = False,
        max_results: int = None,  # REMOVED DEFAULT LIMIT - None means unlimited
        file_extensions: List[str] = None,
        regex_search: bool = False,
        include_hidden: bool = False,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        modified_after: Optional[str] = None,
        modified_before: Optional[str] = None,
        include_preview: bool = False,
        search_sources: List[str] = None  # ['local', 's3'] or specific
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, int]]:
        """
        Perform enhanced file search with local and S3 support - UNLIMITED RESULTS.
        """
        # Default to searching both sources
        if not search_sources:
            search_sources = ['local', 's3']
        
        # Parse date filters
        modified_after_dt = self._parse_date(modified_after) if modified_after else None
        modified_before_dt = self._parse_date(modified_before) if modified_before else None
        
        # Normalize file extensions
        if file_extensions:
            file_extensions = {ext if ext.startswith('.') else f'.{ext}' 
                             for ext in file_extensions}
        
        all_results = []
        total_scanned = 0
        source_counts = {'local': 0, 's3': 0}
        
        # Search local files
        if 'local' in search_sources:
            try:
                local_results, local_scanned = await self._search_local(
                    query=query,
                    search_path=search_path,
                    search_type=search_type,
                    include_folders=include_folders,
                    case_sensitive=case_sensitive,
                    max_results=None,  # No limit for local search
                    file_extensions=file_extensions,
                    regex_search=regex_search,
                    include_hidden=include_hidden,
                    min_size=min_size,
                    max_size=max_size,
                    modified_after_dt=modified_after_dt,
                    modified_before_dt=modified_before_dt,
                    include_preview=include_preview
                )
                all_results.extend([asdict(r) for r in local_results])
                total_scanned += local_scanned
                source_counts['local'] = len(local_results)
            except Exception as e:
                logger.error(f"Local search error: {str(e)}")
        
        # Search S3 objects - NO RESULT LIMIT
        if 's3' in search_sources:
            try:
                s3_results = await self.s3_manager.search_s3_objects(
                    query=query,
                    search_type=search_type,
                    case_sensitive=case_sensitive,
                    max_results=None,  # UNLIMITED S3 RESULTS
                    file_extensions=file_extensions,
                    regex_search=regex_search,
                    include_preview=include_preview,
                    min_size=min_size,
                    max_size=max_size,
                    modified_after=modified_after_dt,
                    modified_before=modified_before_dt
                )
                all_results.extend([asdict(r) for r in s3_results])
                source_counts['s3'] = len(s3_results)
            except Exception as e:
                logger.error(f"S3 search error: {str(e)}")
        
        # Sort results by relevance (name matches first, then by modified date)
        all_results.sort(key=lambda x: (
            0 if x['match_type'] == 'name' else 1,
            -datetime.fromisoformat(x['modified']).timestamp()
        ))
        
        # Apply max_results limit only if specified
        if max_results and max_results > 0:
            all_results = all_results[:max_results]
        
        logger.info(f"Search complete: {len(all_results)} total results returned (was limited: {max_results is not None})")
        
        return all_results, total_scanned, source_counts
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If none work, try ISO format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
            return None

    async def _search_local(self, **kwargs):
        """Search local files - UNLIMITED RESULTS."""
        # Validate and resolve search path
        search_path_obj = self.base_path / kwargs['search_path'].lstrip('/')
        search_path_resolved = search_path_obj.resolve()
        
        # Security check
        if not str(search_path_resolved).startswith(str(self.base_path)):
            raise ValueError("Search path is outside allowed directory")
        
        if not search_path_resolved.exists():
            # Create directory if it doesn't exist
            search_path_resolved.mkdir(parents=True, exist_ok=True)
        
        # Compile regex if needed
        pattern = None
        if kwargs['regex_search']:
            try:
                pattern = re.compile(kwargs['query'], 
                                   re.IGNORECASE if not kwargs['case_sensitive'] else 0)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {str(e)}")
        
        # Perform search
        results = []
        total_scanned = 0
        
        # Use async generator for better memory efficiency
        async for result in self._search_local_generator(
            search_path=search_path_resolved,
            pattern=pattern,
            **kwargs
        ):
            results.append(result)
            total_scanned += 1
            
            # REMOVED: if len(results) >= kwargs['max_results']: break
            # Now processes ALL local files
        
        return results, total_scanned
    
    async def _search_local_generator(self, **kwargs):
        """Async generator for local search results - UNLIMITED."""
        # Extract parameters
        query = kwargs['query']
        search_path = kwargs['search_path']
        search_type = kwargs['search_type']
        include_folders = kwargs['include_folders']
        case_sensitive = kwargs['case_sensitive']
        file_extensions = kwargs['file_extensions']
        pattern = kwargs['pattern']
        include_hidden = kwargs['include_hidden']
        include_preview = kwargs['include_preview']
        
        search_query = query if case_sensitive else query.lower()
        
        # Walk directory tree
        for root, dirs, files in os.walk(search_path):
            # Filter hidden directories if needed
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            # Process ALL files and directories found
            root_path = Path(root)
            
            # Process directories if requested
            if include_folders:
                for dir_name in dirs:
                    if self._matches_local(dir_name, search_query, pattern, case_sensitive):
                        dir_path = root_path / dir_name
                        relative_path = dir_path.relative_to(kwargs['search_path'])
                        
                        yield SearchResult(
                            id=f"local_{abs(hash(str(dir_path)))}",
                            name=dir_name,
                            path=f"/{relative_path}",
                            type='folder',
                            match_type='name',
                            size=None,
                            modified=datetime.fromtimestamp(dir_path.stat().st_mtime).isoformat(),
                            parent_path=f"/{relative_path.parent}" if relative_path.parent != Path('.') else '/',
                            source='local'
                        )
            
            # Process files
            for file_name in files:
                if not include_hidden and file_name.startswith('.'):
                    continue
                
                file_path = root_path / file_name
                
                # Apply extension filter
                if file_extensions:
                    ext = file_path.suffix.lower()
                    if ext not in file_extensions:
                        continue
                
                # Check if file matches
                name_matched = False
                if search_type in ['name', 'both']:
                    if self._matches_local(file_name, search_query, pattern, case_sensitive):
                        name_matched = True
                
                # For wildcard or empty queries, include all files
                if query == '*' or query.strip() == '':
                    name_matched = True
                
                if name_matched:
                    try:
                        stat = file_path.stat()
                        relative_path = file_path.relative_to(kwargs['search_path'])
                        
                        yield SearchResult(
                            id=f"local_{abs(hash(str(file_path)))}",
                            name=file_name,
                            path=f"/{relative_path}",
                            type='file',
                            match_type='name' if name_matched else 'content',
                            size=stat.st_size,
                            modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            parent_path=f"/{relative_path.parent}" if relative_path.parent != Path('.') else '/',
                            extension=file_path.suffix.lower() if file_path.suffix else None,
                            source='local'
                        )
                    except Exception as e:
                        logger.warning(f"Error processing file {file_path}: {e}")
                        continue
    
    def _matches_local(self, text: str, query: str, pattern: Optional[re.Pattern], case_sensitive: bool) -> bool:
        """Check if local file/folder name matches the search criteria."""
        # Special case: if query is '*', match everything
        if query == '*' or query.strip() == '':
            return True
            
        if pattern:
            return bool(pattern.search(text))
        
        search_text = text if case_sensitive else text.lower()
        
        # Support wildcards
        if '*' in query or '?' in query:
            return fnmatch.fnmatch(search_text, query)
        
        return query in search_text

# Main function
def main(args: Dict[str, Any]) -> Dict[str, Any]:
    """Main search function - SHOWS ALL FILES."""
    try:
        logger.info(f"Search called with args: {args}")
        
        # Extract parameters
        query = args.get('query', '*')  # Default to show all files
        search_path = args.get('search_path', '/')
        search_type = args.get('search_type', 'name')
        max_results = args.get('max_results', None)  # None = unlimited
        search_sources = args.get('search_sources', ['s3'])  # Default to S3 only
        
        # S3 configuration
        s3_config = {
            'S3_HOST': args.get('S3_HOST', ''),
            'S3_PORT': args.get('S3_PORT', '443'),
            'S3_ACCESS_KEY': args.get('S3_ACCESS_KEY', ''),
            'S3_SECRET_KEY': args.get('S3_SECRET_KEY', ''),
            'S3_BUCKET_DATA': args.get('S3_BUCKET_DATA', '')
        }
        
        logger.info(f"Search parameters: query='{query}', sources={search_sources}, max_results={max_results}")
        
        # Create file searcher
        base_directory = args.get('base_directory', '/tmp/filemanager')
        searcher = FileSearcher(base_directory, s3_config)
        
        # Run search asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results, total_scanned, source_counts = loop.run_until_complete(
                searcher.search(
                    query=query,
                    search_path=search_path,
                    search_type=search_type,
                    max_results=max_results,
                    search_sources=search_sources,
                    include_folders=args.get('include_folders', True),
                    case_sensitive=args.get('case_sensitive', False),
                    file_extensions=args.get('file_extensions'),
                    regex_search=args.get('regex_search', False),
                    include_hidden=args.get('include_hidden', False),
                    min_size=args.get('min_size'),
                    max_size=args.get('max_size'),
                    modified_after=args.get('modified_after'),
                    modified_before=args.get('modified_before'),
                    include_preview=args.get('include_preview', False)
                )
            )
        finally:
            loop.close()
        
        # Format results for chat interface
        total_results = len(results)
        message = f"Found {total_results} files"
        if total_scanned > total_results:
            message += f" (scanned {total_scanned} total objects)"
        
        # Add source breakdown
        source_info = []
        for source, count in source_counts.items():
            if count > 0:
                source_info.append(f"{count} from {source}")
        if source_info:
            message += f" - {', '.join(source_info)}"
        
        # Create response with options for chat interface
        response = {
            'success': True,
            'results': results,
            'total_found': total_results,
            'total_scanned': total_scanned,
            'source_counts': source_counts,
            'message': message,
            'query': query,
            'search_path': search_path,
            'search_type': search_type
        }
        
        # Add interactive options based on results
        if total_results > 0:
            response['options'] = [
                f'Show all {total_results} files',
                'Filter by file type',
                'Sort by date',
                'Sort by size',
                'Download file',
                'Search again'
            ]
            
            # Add file type breakdown
            file_types = {}
            for result in results:
                ext = result.get('extension', '') or 'no extension'
                file_types[ext] = file_types.get(ext, 0) + 1
            
            if len(file_types) > 1:
                response['file_types'] = file_types
                top_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]
                response['top_file_types'] = top_types
        else:
            response['options'] = [
                'Upload files',
                'Check S3 connection',
                'Try different search',
                'List all files'
            ]
        
        # Add recent files (last 10)
        if results:
            recent_files = sorted(results, key=lambda x: x['modified'], reverse=True)[:10]
            response['recent_files'] = recent_files
        
        logger.info(f"Search completed: {total_results} results returned")
        return response
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            'success': False,
            'error': str(e),
            'results': [],
            'total_found': 0,
            'message': f'Search failed: {str(e)}',
            'options': ['Try again', 'Check configuration']
        }

# Alternative entry point for listing all files
async def list_all_files(args: Dict[str, Any]) -> Dict[str, Any]:
    """Direct function to list ALL files in bucket."""
    try:
        s3_config = {
            'S3_HOST': args.get('S3_HOST', ''),
            'S3_PORT': args.get('S3_PORT', '443'),
            'S3_ACCESS_KEY': args.get('S3_ACCESS_KEY', ''),
            'S3_SECRET_KEY': args.get('S3_SECRET_KEY', ''),
            'S3_BUCKET_DATA': args.get('S3_BUCKET_DATA', '')
        }
        
        s3_manager = S3SearchManager(s3_config)
        all_files = await s3_manager.list_all_s3_objects()
        
        return {
            'success': True,
            'results': [asdict(file) for file in all_files],
            'total_found': len(all_files),
            'message': f'Listed all {len(all_files)} files in bucket',
            'options': ['Download file', 'Filter files', 'Search files'] if all_files else ['Upload files']
        }
        
    except Exception as e:
        logger.error(f"List all files error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'results': [],
            'total_found': 0
        }