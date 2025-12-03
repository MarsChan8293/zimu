from guessit import guessit

# 测试文件名称
file_name = "F1.The.Movie.2025.Hybrid.2160p.WEB-DL.DV.HDR.DDP5.1.Atmos.H265-AOC.mkv"

# 使用guessit解析
result = guessit(file_name)

# 打印解析结果
print("Guessit解析结果:")
for key, value in result.items():
    print(f"  {key}: {value}")

# 测试其他可能的文件名称
print("\n其他测试:")
other_files = [
    "Black.Panther.Wakanda.Forever.2022.2160p.UHD.BluRay.x265.10bit.HDR.TrueHD.7.1.Atmos-RARBG.mkv",
    "Ghost.In.The.Shell.1995.2.0.1080p.BluRay.Remux.H264.HDClub.Rus.Jap.ts"
]

for file in other_files:
    print(f"\n{file}:")
    result = guessit(file)
    for key, value in result.items():
        print(f"  {key}: {value}")