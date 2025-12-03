from __future__ import annotations
from typing import List
from .types import SubtitleItem, SubFormat, Language, MediaInfo


FORMAT_WEIGHT = {
    SubFormat.ASS: 100,
    SubFormat.SRT: 80,
    SubFormat.SUP: 10,
    SubFormat.ZIP: 50,  # archives often include multiple formats
    SubFormat.OTHER: 0,
}

LANG_GROUP_ORDER = [
    [Language.BILINGUAL],
    [Language.SIMPLIFIED],
    [Language.ENGLISH],
    [Language.TRADITIONAL],
]


def _group_key(langs: list[Language]) -> int:
    for idx, group in enumerate(LANG_GROUP_ORDER):
        if any(l in langs for l in group):
            return idx
    return 999


def _format_score(fmt: SubFormat, prefer_format: str) -> int:
    base = FORMAT_WEIGHT.get(fmt, 0)
    # Nudge preferred format higher
    if prefer_format == "ass" and fmt == SubFormat.ASS:
        base += 15
    if prefer_format == "srt" and fmt == SubFormat.SRT:
        base += 15
    return base


def choose_best_subtitle(items: List[SubtitleItem], prefer_format: str, media_info: MediaInfo) -> SubtitleItem | None:
    if not items:
        return None

    def _year_penalty(it: SubtitleItem) -> int:
        if not media_info.year:
            return 0
        return 0 if str(media_info.year) in it.filename_text else 1

    def _download_weight(it: SubtitleItem) -> int:
        # Use download_count primarily once language + format considered
        return it.download_count or 0

    ranked = sorted(
        items,
        key=lambda it: (
            _group_key(it.languages),                # language priority (lower is better)
            -_format_score(it.format, prefer_format),# preferred format boost
            -_download_weight(it),                   # higher download count better
            _year_penalty(it),                       # prefer matching year
            -it.score_hint,                          # custom hints if any
        ),
    )
    return ranked[0] if ranked else None
