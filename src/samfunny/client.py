from __future__ import annotations
import time
from typing import Iterable, List
import re

import requests
from bs4 import BeautifulSoup

from .types import SubtitleItem, Language, SubFormat, MediaInfo

BASE = "https://www.samfunny.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}


def _detect_format(text: str) -> SubFormat:
    t = text.upper()
    # Check for explicit file extensions first
    if ".ASS" in t:
        return SubFormat.ASS
    if ".SRT" in t:
        return SubFormat.SRT
    if ".SUP" in t:
        return SubFormat.SUP
    if ".ZIP" in t:
        return SubFormat.ZIP
    # Check for format keywords as backup
    if "ASS" in t and not any(keyword in t for keyword in ["中英", "双语", "简英"]):
        return SubFormat.ASS
    if "SRT" in t:
        return SubFormat.SRT
    if "SUP" in t:
        return SubFormat.SUP
    if "ZIP" in t:
        return SubFormat.ZIP
    # Check for .sub links - they might be direct downloads
    if ".SUB" in t:
        # Try to determine format from context
        if ".SRT" in t.split(".SUB")[0]:
            return SubFormat.SRT
        if ".ASS" in t.split(".SUB")[0]:
            return SubFormat.ASS
    return SubFormat.OTHER


def _detect_languages(container: BeautifulSoup) -> list[Language]:
    langs: list[Language] = []
    for img in container.find_all("img"):
        src = img.get("src", "")
        if "jollyroger" in src:
            langs.append(Language.BILINGUAL)
        elif "china" in src:
            langs.append(Language.SIMPLIFIED)
        elif "uk" in src:
            langs.append(Language.ENGLISH)
        elif "hongkong" in src:
            langs.append(Language.TRADITIONAL)
    # Textual hints
    text = container.get_text(" ", strip=True)
    if any(k in text for k in ["双语", "中英双语", "简英双语", "chs&eng", "chs_eng"]):
        if Language.BILINGUAL not in langs:
            langs.append(Language.BILINGUAL)
    return langs


class SamfunnyClient:
    def __init__(self, rate_limit: float = 1.2, verbose: bool = False):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.rate_limit = max(rate_limit, 0.0)
        self.verbose = verbose
        self._last_request_ts = 0.0

    def _sleep_if_needed(self):
        now = time.time()
        delta = now - self._last_request_ts
        if delta < self.rate_limit:
            time.sleep(self.rate_limit - delta)

    def _get(self, url: str, referer: str | None = None) -> requests.Response:
        self._sleep_if_needed()
        headers = {}
        if referer:
            headers["Referer"] = referer
        if self.verbose:
            print(f"GET {url}")
        resp = self.session.get(url, headers=headers, timeout=20)
        if self.verbose:
            print(f"Request headers: {resp.request.headers}")
        self._last_request_ts = time.time()
        resp.raise_for_status()
        return resp

    def warmup(self):
        """Visit homepage to establish any cookies or session before search."""
        try:
            r = self._get(BASE)
            if self.verbose:
                print(f"Warmup homepage length={len(r.text)}")
        except Exception as e:
            if self.verbose:
                print(f"Warmup failed: {e}")

    def search_list_page(self, query: str, page: int = 1) -> BeautifulSoup:
        url = f"{BASE}/download/xslist.php?key={requests.utils.quote(query)}"
        if page > 1:
            url += f"&p={page}"
        r = self._get(url)
        return BeautifulSoup(r.text, "lxml")

    def iter_detail_urls(self, query: str, max_pages: int) -> Iterable[str]:
        for p in range(1, max_pages + 1):
            soup = self.search_list_page(query, page=p)
            anchors = soup.select('a[href*="/download/"]')
            count = 0
            for a in anchors:
                href = a.get("href", "")
                if not href:
                    continue
                # Normalize relative
                full = requests.compat.urljoin(BASE, href)
                # Accept both .html and numeric endpoints
                if "/download/" in href and (href.endswith(".html") or re.search(r"/download/\d+", href)):
                    count += 1
                    yield full if full.endswith('.html') else (full if full.endswith('.html') else full + ('' if full.endswith('.html') else '.html'))
            if self.verbose:
                print(f"List page {p}: extracted detail anchors={count}, raw anchors total={len(anchors)}")

    def parse_detail(self, detail_url: str, search_query: str | None = None) -> List[SubtitleItem]:
        referer = None
        if search_query:
            referer = f"{BASE}/download/xslist.php?key={requests.utils.quote(search_query)}"
        r = self._get(detail_url, referer=referer)
        if self.verbose:
            print(f"Detail page length: {len(r.text)}")
            print(f"Contains '字幕文件下载': {'字幕文件下载' in r.text}")
        soup = BeautifulSoup(r.text, "lxml")
        items: List[SubtitleItem] = []

        # Quick truncated-page detection: if essential marker absent, return empty
        if "字幕文件下载" not in r.text and len(r.text) < 2000:
            if self.verbose:
                print("Truncated or anti-bot page received; no subtitle section present.")
            return items

        # Prefer to bound search by the download section if present
        section = None
        for h3 in soup.find_all(["h2", "h3"]):
            if "字幕文件下载" in h3.get_text(strip=True):
                section = h3
                break
        # Find the list container which contains the download links
        container = None
        if section:
            # Look for the sibling div with class "list" which contains download links
            for sibling in section.find_next_siblings():
                if sibling.name == "div" and "list" in sibling.get("class", []):
                    container = sibling
                    break
        if not container:
            container = soup

        # Get all download-related links, not just .sub ones
        all_download_links = container.select('a[href*="/download/"]')
        if self.verbose:
            print(f"Detail {detail_url} found {len(all_download_links)} /download/ anchors")
            # Show some examples for debugging
            for a in all_download_links[:5]:
                print(" - href:", a.get('href'), "text=", a.get_text(strip=True)[:80])
        
        # Process each download link individually
        processed_hrefs = set()
        for a in all_download_links:
            href = a.get("href", "").strip()
            if not href or href in processed_hrefs:
                continue
            processed_hrefs.add(href)
            
            # Skip .html links (probably detail pages, not direct downloads)
            if href.endswith('.html'):
                continue
                
            download_url = requests.compat.urljoin(BASE, href)
            filename_text = a.get_text(strip=True) or href.rsplit("/", 1)[-1]
            
            # Get the row container - should be li or parent div
            li = a.find_parent("li")
            row = li if li is not None else (a.parent if a.parent else container)
            
            # Extract languages
            langs = _detect_languages(row)
            
            # Extract format from text
            row_text = row.get_text(" ", strip=True)
            fmt = _detect_format(row_text)
            
            # Extract download count
            dl_count = None
            dl_div = row.select_one(".shu span") if row else None
            if dl_div:
                try:
                    dl_count = int(dl_div.get_text(strip=True))
                except ValueError:
                    dl_count = None
            
            # Extract other metadata
            size_text = None
            size_div = row.select_one(".size") if row else None
            if size_div:
                size_text = size_div.get_text(strip=True)
            
            source_text = None
            source_span = row.select_one(".zimuzu span") if row else None
            if source_span:
                source_text = source_span.get_text(strip=True)
            
            is_bilingual = Language.BILINGUAL in langs or ("&eng" in row_text.lower()) or ("双语" in row_text)
            
            # Skip unsupported file types
            if href.lower().endswith('.rar'):
                if self.verbose:
                    print(f"Skip .rar archive: {filename_text}")
                continue
            
            # Don't filter by filename extension since some direct downloads might not have proper extensions
            # Instead, let the downloader handle content detection
            items.append(
                SubtitleItem(
                    detail_url=detail_url,
                    download_url=download_url,
                    filename_text=filename_text,
                    languages=langs,
                    format=fmt,
                    referer=detail_url,
                    is_bilingual=is_bilingual,
                    download_count=dl_count,
                    size_text=size_text,
                    source_text=source_text,
                )
            )
        return items

    def search_and_collect(self, media: MediaInfo, max_pages: int) -> List[SubtitleItem]:
        # Optimize query: use only Chinese part for better search results
        query = media.title
        # If title contains multiple languages (has both Chinese and non-Chinese characters), 
        # extract only the Chinese part for search
        chinese_part = ''.join([c for c in query if '\u4e00' <= c <= '\u9fff']).strip()
        if chinese_part and len(chinese_part) < len(query):
            if self.verbose:
                print(f"Optimized search query: '{query}' -> '{chinese_part}'")
            query = chinese_part
        # Warmup once per overall search
        self.warmup()
        # If episode available, some站不支持精确集数检索，先仅用剧名
        collected: List[SubtitleItem] = []
        seen_urls = set()
        
        for detail_url in self.iter_detail_urls(query, max_pages=max_pages):
            try:
                items = self.parse_detail(detail_url, search_query=query)
            except Exception as e:
                if self.verbose:
                    print(f"Detail parse failed {detail_url}: {e}")
                continue
            
            # Filter out duplicate subtitles and add to collection
            for item in items:
                if item.download_url not in seen_urls:
                    seen_urls.add(item.download_url)
                    collected.append(item)
            
            # For TV, prefer items mentioning SxxExx if present
            if media.episode_str:
                ep = media.episode_str
                collected = [it for it in collected if not ep or ep in (it.filename_text or "")]
            
            if self.verbose:
                print(f"Collected unique items total={len(collected)} after {detail_url}")
        return collected
