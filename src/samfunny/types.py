from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional


class Language(Enum):
    BILINGUAL = auto()
    SIMPLIFIED = auto()
    ENGLISH = auto()
    TRADITIONAL = auto()


class SubFormat(Enum):
    ASS = auto()
    SRT = auto()
    SUP = auto()
    ZIP = auto()
    OTHER = auto()


@dataclass
class MediaInfo:
    title: str
    year: Optional[int]
    season: Optional[int]
    episode: Optional[int]

    @property
    def episode_str(self) -> Optional[str]:
        if self.season is None or self.episode is None:
            return None
        return f"S{self.season:02d}E{self.episode:02d}"


@dataclass
class SubtitleItem:
    detail_url: str
    download_url: str
    filename_text: str
    languages: list[Language]
    format: SubFormat
    referer: str
    is_bilingual: bool
    download_count: int | None = None
    size_text: str | None = None
    source_text: str | None = None
    score_hint: int = 0
