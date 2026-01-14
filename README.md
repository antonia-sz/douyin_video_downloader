# 抖音视频批量下载工具

一个简单高效的 Python 脚本，用于从抖音链接中批量下载mp4视频。

## ✨ 功能特性

- **批量下载** - 从 Excel 文件读取抖音分享链接，自动批量下载
- **智能识别** - 自动识别 Excel 中包含"链接"或"url"的列
- **高清优先** - 优先下载 720p 高清视频，若无则选择其他可用格式
- **断点续传** - 已下载的有效视频自动跳过，避免重复下载
- **自动重试** - 下载失败自动重试（最多3次）
- **失败记录** - 记录所有失败链接及原因，方便排查

## 📋 环境要求

- Python 3.6+
- 依赖库：`requests`, `pandas`, `tqdm`, `openpyxl`

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install requests pandas tqdm openpyxl
```

### 2. 准备 Excel 文件

创建一个 Excel 文件（如 `input_data.xlsx`），包含一列抖音分享链接。列名需包含"链接"或"url"字样。

示例：

| 视频链接 |
|---------|
| https://v.douyin.com/xxxxx |
| https://v.douyin.com/yyyyy |

### 3. 配置脚本

打开 `douyin_video_downloader.py`，修改以下配置项：

```python
# Excel 文件路径
EXCEL_PATH = "input_data.xlsx"

# 视频保存目录
SAVE_DIR = "videos"

# 测试模式：设为数字只处理前 N 条，设为 None 处理全部
TEST_N = None

# 视频解析 API（需要自行获取，推荐Parsevideo）
API_BASE = "你的视频解析API"
```

### 4. 运行脚本

```bash
python douyin_video_downloader.py
```

## 📁 输出说明

- 视频文件保存在 `videos` 目录下
- 文件名格式：`{视频ID}.mp4`
- 运行结束后会显示成功/失败统计及失败原因

## ⚠️ 注意事项

1. **API 配置**：需要配置有效的视频解析 API 才能使用，解析API推荐Parsevideo，网址https://pv.vlogdownloader.com/
2. **合规使用**：请遵守相关法律法规，仅供学习研究使用
3. **版权声明**：下载的视频版权归原作者所有

## 📄 License

MIT License
