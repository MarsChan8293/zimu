from pathlib import Path
from guessit import guessit
from src.samfunny.filename_parser import parse_media_info

# 测试文件名称
files_to_test = [
    "F1.The.Movie.2025.Hybrid.2160p.WEB-DL.DV.HDR.DDP5.1.Atmos.H265-AOC.mkv",
    "Black.Panther.Wakanda.Forever.2022.2160p.UHD.BluRay.x265.10bit.HDR.TrueHD.7.1.Atmos-RARBG.mkv",
    "Ghost.In.The.Shell.1995.2.0.1080p.BluRay.Remux.H264.HDClub.Rus.Jap.ts"
]

# 测试parse_media_info函数
print("测试parse_media_info函数:")
for file_name in files_to_test:
    path = Path(file_name)
    
    # 打印guessit的完整结果
    guess_result = guessit(file_name)
    print(f"\n文件名: {file_name}")
    print("  Guessit完整结果:")
    for key, value in guess_result.items():
        print(f"    {key}: {value}")
    
    # 测试parse_media_info函数
    info = parse_media_info(path)
    print(f"  Parse_media_info结果:")
    print(f"    标题: {info.title}")
    print(f"    年份: {info.year}")
    print(f"    季度: {info.season}")
    print(f"    集数: {info.episode}")
    print(f"    集数字符串: {info.episode_str}")