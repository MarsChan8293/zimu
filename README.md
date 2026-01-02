# 自动下载双语字幕工具（Samfunny 源）

一个命令行工具：扫描当前目录媒体文件，使用 samfunny.com 搜索并下载字幕，优先中英双语；无双语时简体优先；内置 zip 解压，自动将 `.srt/.ass` 放到视频同名路径旁。

## 特性
- 基于标题搜索，抓取详情页“字幕文件下载”区块
- 语言优先级：双语 > 简体 > 英文 > 繁体
- 格式偏好：ASS/SSA > SRT（可通过参数调整）
- 支持 zip 自动解压，rar/7z 暂不支持（提示跳过）
- 轻量节流与重试；下载时携带 Referer 与 cookies
- 支持递归遍历所有子目录（可选）

## 安装

### 方式一：使用 pip 安装（推荐）
```powershell
# 克隆仓库后，在项目根目录执行
pip install -e .

# 或直接从 GitHub 安装（如果已推送）
pip install git+https://github.com/yourusername/zimu.git
```

### 方式二：手动安装依赖
```powershell
pip install requests beautifulsoup4 lxml guessit tenacity tqdm
```

## 使用

安装后，可在任意目录下直接执行 `zimu` 命令：

```powershell
# 仅当前目录，模拟运行
zimu --dry-run
# 仅当前目录，指定参数
zimu --max-pages 2 --prefer-format ass --rate-limit 1.5
# 递归遍历所有子目录
zimu --recursive
# 或使用短选项
zimu -r
```

常用参数：
- `--max-pages`：搜索分页最大页数（默认 2）
- `--prefer-format`：`ass|srt`（默认 `ass`）
- `--dry-run`：仅打印拟执行动作，不进行网络下载
- `--rate-limit`：页面请求的最小间隔秒数（默认 1.2）
- `--recursive`, `-r`：递归遍历所有子目录
- `--verbose`：启用详细日志输出

## 注意
- 若下载链接过期，程序会刷新详情页重试。
- rar/7z 文件将被跳过并提示；后续版本可选接入 7-Zip。
- 请尊重目标站点的访问频率，避免高频抓取。

## 许可
仅供学习与个人使用。请遵守目标站点的使用条款与当地法律法规。