import argparse
import os
import sys
from pathlib import Path
from typing import List

from samfunny.filename_parser import parse_media_info
from samfunny.client import SamfunnyClient
from samfunny.scoring import choose_best_subtitle, _format_score
from samfunny.downloader import download_and_place
from samfunny.types import SubFormat


VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".ts", ".webm"}


def find_media_files(root: Path, recursive: bool = False) -> List[Path]:
    files: List[Path] = []
    if recursive:
        # 使用glob递归遍历所有子目录
        for ext in VIDEO_EXTS:
            for file in root.glob(f"**/*{ext}"):
                if file.is_file():
                    files.append(file)
    else:
        # 只遍历当前目录
        for entry in root.iterdir():
            if entry.is_file() and entry.suffix.lower() in VIDEO_EXTS:
                files.append(entry)
    return sorted(files)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="zimu",
        description="Download subtitles from samfunny.com for media files in current directory",
    )
    p.add_argument("--max-pages", type=int, default=2, help="Max pages to search per query")
    p.add_argument(
        "--prefer-format",
        choices=["ass", "srt"],
        default="ass",
        help="Preferred subtitle format when multiple available",
    )
    p.add_argument("--rate-limit", type=float, default=1.2, help="Min seconds between page requests")
    p.add_argument("--dry-run", action="store_true", help="Print planned actions without network downloads")
    p.add_argument("--verbose", action="store_true", help="Verbose logging")
    p.add_argument("--recursive", "-r", action="store_true", help="Recursively search all subdirectories")
    return p


def main(argv: List[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    root = Path(os.getcwd())
    media_files = find_media_files(root, recursive=args.recursive)

    if not media_files:
        print("No media files found in current directory.")
        return 0

    client = SamfunnyClient(rate_limit=args.rate_limit, verbose=args.verbose)

    for media in media_files:
        # 跳过sample开头的视频文件
        if media.name.lower().startswith('sample'):
            print(f"\n>>> Skipping: {media.name} (sample file)")
            continue
        
        # 检查是否已经有字幕文件
        ass_path = media.with_suffix('.ass')
        srt_path = media.with_suffix('.srt')
        if ass_path.exists() or srt_path.exists():
            print(f"\n>>> Skipping: {media.name} (subtitle already exists)")
            continue
        
        print(f"\n>>> Processing: {media.name}")
        info = parse_media_info(media)
        if args.verbose:
            print(f"Parsed: title={info.title}, year={info.year}, episode={info.episode_str}")

        print(f"Search query used for Samfunny: {info.title}")
        try:
            results = client.search_and_collect(info, max_pages=args.max_pages)
        except Exception as e:
            print(f"Search failed for {media.name}: {e}")
            continue

        if not results:
            print("No subtitles found on Samfunny.")
            continue

        # Separate zip files and direct downloads for better handling
        zip_subtitles = [item for item in results if item.format == SubFormat.ZIP or '.zip' in item.filename_text.lower()]
        direct_subtitles = [item for item in results if item.format in (SubFormat.SRT, SubFormat.ASS) or any(ext in item.filename_text.lower() for ext in ['.srt', '.ass'])]
        
        # First try all zip files, they are more reliable
        for i, sub_item in enumerate(sorted(zip_subtitles, key=lambda it: (
            -it.download_count if it.download_count else 0
        ))[:3]):
            if args.dry_run:
                print(f"[DRY-RUN] Would download: {sub_item.filename_text} ({sub_item.format}) from {sub_item.detail_url}")
                continue

            try:
                print(f"Trying ZIP subtitle {i+1}/3: {sub_item.filename_text}")
                out_path = download_and_place(client.session, sub_item, media)
                print(f"Saved: {out_path}")
                break  # Success! Move to next media file
            except Exception as e:
                print(f"ZIP download failed for {sub_item.filename_text}: {e}")
                continue
        else:
            # If no zip success, try direct downloads
            for i, sub_item in enumerate(sorted(direct_subtitles, key=lambda it: (
                -_format_score(it.format, args.prefer_format),
                -it.download_count if it.download_count else 0
            ))[:3]):
                if args.dry_run:
                    print(f"[DRY-RUN] Would download: {sub_item.filename_text} ({sub_item.format}) from {sub_item.detail_url}")
                    continue

                try:
                    print(f"Trying direct subtitle {i+1}/3: {sub_item.filename_text}")
                    out_path = download_and_place(client.session, sub_item, media)
                    print(f"Saved: {out_path}")
                    break  # Success! Move to next media file
                except Exception as e:
                    print(f"Direct download failed for {sub_item.filename_text}: {e}")
                    continue
            else:
                # All attempts failed
                print(f"All subtitle attempts failed for {media.name}")
                continue

    return 0


if __name__ == "__main__":
    sys.exit(main())
