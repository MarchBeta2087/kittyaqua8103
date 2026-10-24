# text_packager.py
# 221 lines of code, including annotations and blank lines
# Time: 2026-06-19T15:00:00+08:00
# Copyright (c) 2026 MarchBeta2087
# SPDX-License-Identifier: MIT

import json
import re
import subprocess
from datetime import datetime
import pytz
from tzlocal import get_localzone
from pathlib import Path

tz = pytz.timezone(get_localzone().key)
time_text = datetime.now(tz).isoformat(timespec='seconds')

MAINLINE_TIMELINE = "2033-11-13"
MAIN_BRANCHES = {"main", "master"}
ALT_PREFIX = "alt/"
ALT_FIELDS = ("作者", "锚点", "分歧点", "与主线差异")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_branch():
    """返回当前 Git 分支名；不在 Git 仓库或没有 Git 时返回 None。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def parse_alt_declaration(file_path = Path("ALT.md")):
    """解析 ALT.md 的四个字段，缺失或为空时抛 ValueError。"""
    if not file_path.exists():
        raise ValueError(f"{file_path} 不存在：alt 分支必须提供分支声明，模板见 ALT.example.md")
    fields = {}
    current = None
    in_code_block = False
    for raw_line in file_path.read_text(encoding = "utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        line = line.lstrip(">").strip()
        if not line:
            continue
        match = re.match(r"^[-*]?\s*(" + "|".join(ALT_FIELDS) + r")\s*[：:]\s*(.*)$", line)
        if match:
            current = match.group(1)
            fields[current] = match.group(2).strip()
        elif current == "与主线差异":
            fields[current] += "\n" + line
    missing = [field for field in ALT_FIELDS if not fields.get(field, "").strip()]
    if missing:
        raise ValueError(f"{file_path} 缺少字段或字段为空：{'、'.join(missing)}")
    return fields


def check_timeline(meta_json, branch):
    """校验 timeline 与当前分支是否匹配，返回打包标题所需的信息。"""
    timeline = str(meta_json.get("timeline", "")).strip()
    if not timeline:
        raise ValueError("meta.json 缺少 timeline 字段（格式 YYYY-MM-DD）")
    if not DATE_PATTERN.match(timeline):
        raise ValueError(f"meta.json 的 timeline 必须为 YYYY-MM-DD，当前为 {timeline}")

    if branch is None:
        print("警告：未检测到 Git 分支，跳过时间线锁定校验")
        return {"timeline": timeline, "branch": None, "author": None, "diverge": None}

    if branch in MAIN_BRANCHES:
        if timeline != MAINLINE_TIMELINE:
            raise ValueError(
                f"主线 {branch} 的 timeline 必须为 {MAINLINE_TIMELINE}，当前为 {timeline}；"
                "如需其他时间点，请新建 alt/<author>/<diverge> 分支或 fork"
            )
        return {"timeline": timeline, "branch": branch, "author": None, "diverge": None}

    if branch.startswith(ALT_PREFIX):
        parts = branch.split("/")
        if len(parts) != 3 or not parts[1].strip() or not parts[2].strip():
            raise ValueError(f"alt 分支必须命名为 alt/<author>/<diverge>，当前为 {branch}")
        author = parts[1]
        if timeline == MAINLINE_TIMELINE:
            raise ValueError(f"alt 分支的时间线不得与主线相同（{MAINLINE_TIMELINE}）")
        declaration = parse_alt_declaration()
        if declaration["锚点"] != timeline:
            raise ValueError(
                f"ALT.md 的锚点（{declaration['锚点']}）必须与 meta.json 的 timeline（{timeline}）一致"
            )
        if not DATE_PATTERN.match(declaration["分歧点"]):
            raise ValueError(f"ALT.md 的分歧点必须为 YYYY-MM-DD，当前为 {declaration['分歧点']}")
        if declaration["分歧点"] > timeline:
            raise ValueError("ALT.md 的分歧点不得晚于锚点")
        if author.lower() not in declaration["作者"].lower():
            print(f"警告：分支名中的作者 {author} 未出现在 ALT.md 的“作者”字段中")
        return {
            "timeline": timeline,
            "branch": branch,
            "author": declaration["作者"],
            "diverge": declaration["分歧点"],
        }

    print(f"提示：当前分支 {branch} 既不是主线也不是 alt，跳过时间线锁定校验")
    return {"timeline": timeline, "branch": branch, "author": None, "diverge": None}

def get_file_list(directory, path = Path(), depth = 1):
    if type(directory) == list:
        file_list = []
        for child in directory:
            if type(child) == dict:
                try:
                    if ('/' not in child["name"]) and ('\\' not in child["name"]):
                        file_path = path / child["name"]
                        try:
                            if child["type"] == "file":
                                file_list.append({"file_name": file_path.resolve(), "depth": depth})
                            elif child["type"] == "directory":
                                try:
                                    file_list.append({"title": child["title"], "depth": depth + 1})
                                    file_list += get_file_list(child["children"], file_path, depth + 1)
                                except KeyError:
                                    raise ValueError("子对象 title 字段或 children 字段缺失")
                        except KeyError:
                            raise ValueError("子对象 type 字段缺失")
                    else:
                        raise ValueError("name 字段的值不得包含斜杠和反斜杠")
                except KeyError:
                    raise ValueError("子对象 name 字段缺失")
            else:
                raise ValueError("children 的值数组内元素必须均为对象")
        return file_list
    else:
        raise ValueError("children 的值类型必须为数组")

if __name__ == "__main__":
    try:
        # 读取 meta.json
        meta_file = open(Path("meta.json").resolve(), "r", encoding = "utf-8")
        meta_content = meta_file.read()

        # 提取内容
        try:
            meta_json = json.loads(meta_content)
        except json.decoder.JSONDecodeError:
            raise ValueError("不符合 JSON 格式规范")
        
        # 获取标题和版本标签
        try:
            project_title_version = meta_json["title"] + " " + meta_json["version_tag"]
        except KeyError:
            raise ValueError("请补充根对象 title 和 version_tag 字段")

        # 校验时间线（main 锁定 2033-11-13，alt/* 必须偏离该日期）
        timeline_info = check_timeline(meta_json, get_branch())

        # 读取项目结构
        try:
            if meta_json["type"] == "project":
                try:
                    project_structure = meta_json["children"]
                except KeyError:
                    raise ValueError("请补充根对象 children 字段")
            else:
                raise ValueError("根对象 type 的值必须为 project")
        except KeyError:
            raise ValueError("请补充根对象 type 字段")

        # 获取文件列表
        file_list = get_file_list(project_structure)
        
        # 打包文件
        packaged_title = project_title_version + " · 时间线 " + timeline_info["timeline"]
        if timeline_info["author"]:
            packaged_title += (
                " · 分支 " + timeline_info["branch"]
                + " · 作者 " + timeline_info["author"]
                + " · 分歧点 " + timeline_info["diverge"]
            )
        packaged_lines = ["# " + packaged_title, ""]
        for item in file_list:
            if "file_name" in item:
                file_name = item["file_name"]
                if file_name.suffix.lower() == ".md":
                    try:
                        f = open(file_name, "r", encoding = "utf-8")
                        for line in f:
                            newline = line
                            if line.startswith("#"):
                                newline = "#" * item["depth"] + newline
                            packaged_lines.append(newline.rstrip("\r\n"))
                        packaged_lines.append("")
                    except FileNotFoundError:
                        raise ValueError(f"{file_name} 不存在")
                else:
                    raise ValueError("仅支持 Markdown 文件（.md）")
            else:
                packaged_lines.append('#' * item["depth"] + " " + item["title"])
                packaged_lines.append("")
        packaged_file_path = Path("packaged_file.md").resolve()
        packaged_file = open(packaged_file_path, "w", encoding = "utf-8")
        for line in packaged_lines:
            packaged_file.write(line + "\n")
        packaged_file.write("（本文件由 text_packager.py 自动生成，请勿手工修改）" + "\n")
        packaged_file.write("（文档结束）" + "\n\n" + time_text + "\n")

        meta_file.close()
        packaged_file.close()

        print(f"成功打包为 {packaged_file_path}")
    except FileNotFoundError:
        raise FileNotFoundError("请在本目录添加 meta.json")
