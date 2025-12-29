"""
脚本名称：douyin_video_downloader.py
功能说明：抖音视频批量下载工具

主要功能：
1. 从 Excel 文件中读取抖音分享链接（自动识别包含"链接"或"url"的列）
2. 调用第三方解析 API将分享链接转换为可下载的真实视频地址，解析API推荐Parsevideo，网址https://pv.vlogdownloader.com
3. 优先下载 720p 高清视频，若无则选择其他可用格式
4. 支持断点续传：已下载的有效视频文件会自动跳过
5. 下载失败自动重试（最多3次），并记录所有失败链接及原因

配置项：
- EXCEL_PATH: Excel 文件路径
- SAVE_DIR: 视频保存目录
- TEST_N: 测试模式下只处理前 N 条（设为 None 则处理全部）
- MIN_VALID_SIZE: 判定下载成功的最小文件大小阈值

输出：视频文件保存在 videos 目录，文件名为视频ID.mp4
"""

import os
import re
import time
import hashlib
import urllib.parse as up

import requests
import pandas as pd
from tqdm import tqdm

# =========================
# 1. 配置区（按需修改）
# =========================

# 你的 Excel 文件名（和本脚本放在同一文件夹）
EXCEL_PATH = "input_data.xlsx"      # 请修改为实际文件名

# 视频输出目录
SAVE_DIR = "videos"

# 是否只试跑前 N 条；想全量就改为 None
TEST_N = None   # 之前用 10 试跑，现在可以设为 None 跑全部

# Parsevideo视频解析 API
API_BASE = "你的视频解析API"

# 认为“下载成功”的最小文件大小（字节）
MIN_VALID_SIZE = 50_000  # 50KB，可按需调大一点


# =========================
# 2. 解析 API 相关函数
# =========================

def extract_play_url_from_data(data):
    """
    从解析 API 返回的数据结构中挑选一个最合适的播放链接（mp4 流）
    规则：
    1. 优先 normal_720（720p高清）
    2. 再找所有包含“720”的格式
    3. 如果都没有，取 formats[0]
    """
    if not isinstance(data, dict):
        return None, f"API 返回非 dict 类型：{type(data)}"

    formats = data.get("data", {}).get("formats", [])
    if not formats:
        return None, "data.data.formats 为空"

    # ① 优先 normal_720
    for f in formats:
        fmt = f.get("format", "")
        if "normal_720" in fmt:
            url = f.get("url")
            if url:
                return url, None

    # ② 其次：找所有 720
    for f in formats:
        fmt = f.get("format", "")
        if "720" in fmt:
            url = f.get("url")
            if url:
                return url, None

    # ③ 都没有就用第一个
    url = formats[0].get("url")
    if url:
        return url, None
    else:
        return None, "formats 中未找到 url 字段"


def call_parse_api(share_url):
    """
    调用 vlogdownloader 的 API，将抖音分享链接转换为真实可下载的播放链接。
    返回: (play_url, error_reason)
      - play_url: 正常时为字符串，失败时为 None
      - error_reason: 失败原因字符串，成功时为 None
    """
    api_url = API_BASE + up.quote(share_url, safe="")
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "parsevideo api/v1",
    }

    try:
        resp = requests.get(api_url, headers=headers, timeout=30)
        resp.raise_for_status()

        # 尝试按 JSON 解析
        try:
            data = resp.json()
        except ValueError:
            return None, f"API 返回非 JSON 文本：{resp.text[:200]}"

        play_url, err = extract_play_url_from_data(data)
        if not play_url:
            return None, f"未获取到播放链接：{err}；原始返回片段：{str(data)[:200]}"

        return play_url, None

    except Exception as e:
        return None, f"请求异常：{e}"


# =========================
# 3. 下载相关函数
# =========================

def get_video_id(url):
    """从原始链接里提取 video_id，如果没有就用 md5 生成一个"""
    m = re.search(r'/video/(\d+)', url)
    if m:
        return m.group(1)
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:12]


def download_file(file_url, save_path):
    """
    下载文件（流式），简单重试 3 次
    返回: (ok, error_reason)
      - ok: True/False
      - error_reason: 失败原因（成功时为 None）
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    last_err = None

    for attempt in range(3):
        try:
            with requests.get(file_url, headers=headers, timeout=60, stream=True) as r:
                r.raise_for_status()
                with open(save_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            # 简单验证文件大小
            if os.path.getsize(save_path) > MIN_VALID_SIZE:
                return True, None
            else:
                last_err = f"文件太小（<{MIN_VALID_SIZE} 字节），可能无效"
                os.remove(save_path)
        except Exception as e:
            last_err = f"第 {attempt+1} 次下载异常：{e}"
            time.sleep(2)

    return False, last_err or "未知原因"


# =========================
# 4. 主流程
# =========================

def main():
    start_time = time.time()

    os.makedirs(SAVE_DIR, exist_ok=True)

    # 读取 Excel
    df = pd.read_excel(EXCEL_PATH)

    # 自动找“链接”这一列（包含“链接”或“url”字样）
    link_col = None    # type: ignore
    for col in df.columns:
        if "链接" in col or "url" in col.lower():
            link_col = col
            break

    if not link_col:
        raise ValueError("未找到包含链接的列，请检查 Excel 列名。")

    links = df[link_col].dropna().tolist()

    # 试跑：只取前 TEST_N 条
    if TEST_N is not None:
        links = links[:TEST_N]

    success = 0
    failures = []   # 存 (url, reason)

    print(f"开始处理，共 {len(links)} 条链接…\n")

    for share_url in tqdm(links, desc="下载中"):
        vid = get_video_id(share_url)
        save_path = os.path.join(SAVE_DIR, f"{vid}.mp4")

        # ✅ 功能 1：如果之前已经成功下载过（文件存在且大小>阈值），完全跳过，不再请求 API
        if os.path.exists(save_path) and os.path.getsize(save_path) > MIN_VALID_SIZE:
            # print(f"已存在且有效，跳过：{share_url}")
            continue

        # 调用解析 API
        play_url, err = call_parse_api(share_url)
        if not play_url:
            failures.append((share_url, f"解析失败：{err}"))
            continue

        # 下载视频
        ok, err = download_file(play_url, save_path)
        if ok:
            success += 1
        else:
            failures.append((share_url, f"下载失败：{err}"))

    end_time = time.time()
    elapsed = end_time - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print("\n===== 完成 =====")
    print(f"成功：{success}")
    print(f"失败：{len(failures)}")
    print(f"耗时：{minutes} 分 {seconds} 秒（约 {elapsed:.1f} 秒）")

    if failures:
        print("\n以下是所有下载失败的链接及原因：")
        for url, reason in failures:
            print("-" * 80)
            print("链接：", url)
            print("原因：", reason)


if __name__ == "__main__":
    main()
