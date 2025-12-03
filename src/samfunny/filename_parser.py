from __future__ import annotations
from pathlib import Path
from typing import Optional
from guessit import guessit

from .types import MediaInfo


def parse_media_info(path: Path) -> MediaInfo:
    info = guessit(path.name)
    
    # 优化标题解析：处理guessit将"F1"识别为film的情况
    title = str(info.get("title", path.stem)).strip()
    
    # 检查是否有film字段，如"F1"被识别为film:1
    film = info.get("film")
    if film:
        title = f"F{film} {title}" if title else f"F{film}"
    
    # 如果标题仍然太短或不太可能是完整标题，尝试重新构建
    elif len(title) < 8:
        # 直接使用文件名的前缀作为标题
        stem = path.stem
        # 移除常见的后缀
        for suffix in [".hybrid", ".dv", ".hdr", ".uhd", ".bluray", ".web-dl"]:
            if suffix in stem.lower():
                stem = stem.lower().split(suffix)[0]
        # 移除年份
        import re
        stem = re.sub(r"\.\d{4}$", "", stem)
        # 移除分辨率
        stem = re.sub(r"\.\d{3,4}p$", "", stem)
        # 替换点为空格
        title = stem.replace(".", " ").strip()
    
    year: Optional[int] = info.get("year")
    season: Optional[int] = info.get("season")
    episode: Optional[int] = info.get("episode")
    return MediaInfo(title=title, year=year, season=season, episode=episode)
