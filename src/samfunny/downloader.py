from __future__ import annotations
import io
import os
import re
import zipfile
from pathlib import Path
from typing import Optional

import requests

from .types import SubtitleItem


def _pick_from_zip(zf: zipfile.ZipFile, prefer_format: str) -> Optional[tuple[str, bytes]]:
    names = zf.namelist()
    # Filter to subtitle files
    cands = [n for n in names if n.lower().endswith((".ass", ".srt"))]
    if not cands:
        return None
    # Preferred format first
    if prefer_format == "ass":
        for n in cands:
            if n.lower().endswith(".ass"):
                with zf.open(n) as fh:
                    return n, fh.read()
    if prefer_format == "srt":
        for n in cands:
            if n.lower().endswith(".srt"):
                with zf.open(n) as fh:
                    return n, fh.read()
    # else first available
    n = cands[0]
    with zf.open(n) as fh:
        return n, fh.read()


def _final_sub_path(video_path: Path, picked_name: str) -> Path:
    ext = ".ass" if picked_name.lower().endswith(".ass") else ".srt"
    return video_path.with_suffix(ext)


def download_and_place(session: requests.Session, item: SubtitleItem, video_path: Path, prefer_format: str = "ass") -> Path:
    # Download with referer header
    headers = {"Referer": item.referer}
    r = session.get(item.download_url, headers=headers, timeout=60, allow_redirects=True)
    r.raise_for_status()
    
    # Check if the response is likely an error page, anti-scraping response, or 'file not found' message
    content = r.content
    
    # Check for common Chinese error messages
    try:
        content_str = content.decode('utf-8', errors='replace')
        if '文件不存在' in content_str or '下载失败' in content_str or '无权访问' in content_str:
            raise RuntimeError(f"Download failed: Website returned error message '{content_str.strip()}'. URL: {item.download_url}")
    except:
        pass
    
    # Check for general short error responses
    if len(content) < 100:
        if b'html' in content.lower() or len(content) < 20:
            try:
                short_content = content.decode('utf-8', errors='replace')
                raise RuntimeError(f"Download returned error/anti-scraping response instead of subtitle file (got '{short_content.strip()}', {len(content)} bytes). URL: {item.download_url}")
            except:
                raise RuntimeError(f"Download returned error/anti-scraping response instead of subtitle file (got {len(content)} bytes). URL: {item.download_url}")

    # Infer filename and content
    cd = r.headers.get("Content-Disposition", "")
    raw_name = item.filename_text
    
    # Improved Content-Disposition parsing with fallback logic
    fname_match = re.search(r'filename\*?=(?:UTF-8\'\'|\'\')?([^;]+)', cd, re.IGNORECASE)
    if fname_match:
        raw_name = fname_match.group(1).strip()
        # Remove quotes if present
        raw_name = raw_name.strip('"')
        # Handle URL-encoded characters
        raw_name = requests.utils.unquote(raw_name)

    content = r.content
    
    # Zip handling first - always check by magic bytes for reliability
    out_path: Path
    if len(content) >= 4 and content[:2] == b'PK':
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            picked = _pick_from_zip(zf, prefer_format)
            if not picked:
                raise RuntimeError("ZIP file contains no .srt/.ass")
            picked_name, picked_bytes = picked
            out_path = _final_sub_path(video_path, picked_name)
            out_path.write_bytes(picked_bytes)
            return out_path

    # Process content with BOM stripping and improved detection
    # Read content with proper encoding handling and BOM stripping
    content_str = ""
    try:
        # Try UTF-8 with BOM stripping first
        content_str = content.decode('utf-8-sig', errors='replace')
    except:
        # Fallback to other encodings if needed
        try:
            content_str = content.decode('gbk', errors='replace')
        except:
            content_str = content.decode('latin-1')
    
    # Normalize newlines and remove leading/trailing whitespace for better detection
    content_str_normalized = content_str.replace('\r\n', '\n').replace('\r', '\n').strip()
    
    # Check for .ass files (ASS files start with [Script Info])
    is_ass = False
    if content_str_normalized.startswith('[Script Info]'):
        is_ass = True
    elif '[Script Info]' in content_str_normalized[:2000]:
        is_ass = True
    
    # Check for .srt files (SRT format: number, timecode, text, blank line)
    is_srt = False
    if not is_ass:
        # Check for common SRT patterns
        srt_patterns = [
            # Check for numeric index followed by timecode pattern
            re.compile(r'^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}'),
            # Check for timecode pattern anywhere in the file
            re.compile(r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}')
        ]
        for pattern in srt_patterns:
            if pattern.search(content_str_normalized[:2000]):
                is_srt = True
                break
        # Additional check: many SRT files have multiple numeric entries
        if not is_srt:
            srt_entry_count = len(re.findall(r'^\d+\s*$', content_str_normalized, re.MULTILINE))
            if srt_entry_count > 3:
                is_srt = True
    
    # Save the file based on detected content type
    if is_ass:
        out_path = video_path.with_suffix('.ass')
        out_path.write_bytes(content)
        return out_path
    elif is_srt:
        out_path = video_path.with_suffix('.srt')
        out_path.write_bytes(content)
        return out_path

    # If we got here, it's an unsupported file type
    # Try to detect what type it might be for better error reporting
    detected_type = "Unknown"
    if len(content) >= 4:
        if content[:4] == b'Rar!':
            detected_type = "RAR archive (unsupported)"
        elif content[:3] == b'7zX':
            detected_type = "7Z archive (unsupported)"
        elif content[:2] == b'PK':
            detected_type = "ZIP archive (should have been handled earlier)"
        elif content[:4] == b'BM60':
            detected_type = "SUP subtitle (unsupported)"
        elif content[:4] == b'fLaC':
            detected_type = "FLAC audio (unsupported)"
        elif content[:4] == b'OggS':
            detected_type = "OGG media (unsupported)"
    
    # Additional content analysis for text files
    if len(content_str) > 0:
        # Count line breaks and check if it's text-based
        newline_count = content_str.count('\n')
        if newline_count > 10:
            # More than 10 lines - likely a text file
            # Check for common subtitle patterns that might have been missed
            has_timecodes = re.search(r'\d{2}:\d{2}:\d{2}', content_str[:2000])
            has_numbers = re.search(r'^\d+', content_str, re.MULTILINE)
            
            if has_timecodes:
                # Has timecodes - likely a subtitle file, try to save as SRT
                out_path = video_path.with_suffix('.srt')
                out_path.write_bytes(content)
                return out_path
            elif has_numbers and newline_count > 50:
                # Has numbers at start of lines and many lines - likely SRT
                out_path = video_path.with_suffix('.srt')
                out_path.write_bytes(content)
                return out_path
            
            detected_type = f"Text file (has {newline_count} lines, timecodes: {has_timecodes}, numbers: {has_numbers})"
        elif all(c.isprintable() or c in '\n\t\r' for c in content_str[:1000]):
            detected_type = f"Short text file ({len(content_str)} chars)"
        else:
            detected_type = "Binary file (unsupported format)"
    
    raise RuntimeError(f"Unsupported subtitle file type: {raw_name}. Detected: {detected_type}. Only direct .srt/.ass and .zip supported in V1")
