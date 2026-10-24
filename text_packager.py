# text_packager.py
# Version: 1.1
# 467 lines of code, including annotations and blank lines
# Created: 2026-06-19T15:00:00+08:00
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

TOOL_VERSION = "1.1"

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")

POLICY_DEFAULTS = {
    "enforce_timeline": True,
    "mainline": None,
    "main_branches": ["main", "master"],
    "alt_branch_pattern": "alt/<author>/<diverge>",
    "alt_declaration": "ALT.md",
    "alt_declaration_fields": {
        "author": "作者",
        "anchor": "锚点",
        "diverge": "分歧点",
        "differences": "与主线差异",
    },
    "alt_diff_section": "与主线的差异",
}

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

def load_policy(meta_json):
    """读取并校验 meta.json 的 policy；未声明时返回 None（纯打包模式）。"""
    raw = meta_json.get("policy")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("policy 字段的值必须为对象")

    unknown = set(raw) - set(POLICY_DEFAULTS)
    if unknown:
        raise ValueError(f"policy 含未知字段：{'、'.join(sorted(unknown))}")

    policy = dict(POLICY_DEFAULTS)
    policy.update(raw)

    if not isinstance(policy["enforce_timeline"], bool):
        raise ValueError("policy.enforce_timeline 必须为布尔值")
    if not policy["enforce_timeline"]:
        return policy

    mainline = str(policy["mainline"] or "").strip()
    if not DATE_PATTERN.match(mainline):
        raise ValueError("已启用 policy.enforce_timeline，policy.mainline 必须为 YYYY-MM-DD")
    policy["mainline"] = mainline

    branches = policy["main_branches"]
    if (not isinstance(branches, list) or not branches
            or not all(isinstance(branch, str) and branch.strip() for branch in branches)):
        raise ValueError("policy.main_branches 必须为非空字符串数组")

    pattern = str(policy["alt_branch_pattern"]).strip()
    pattern_segments = pattern.split("/")
    if (len(pattern_segments) < 2
            or pattern_segments[0].startswith("<")
            or "<author>" not in pattern_segments
            or "<diverge>" not in pattern_segments):
        raise ValueError("policy.alt_branch_pattern 的第一段必须为字面量，且必须包含 <author> 与 <diverge>")
    policy["alt_branch_pattern"] = pattern

    declaration = str(policy["alt_declaration"]).strip()
    if not declaration:
        raise ValueError("policy.alt_declaration 必须为非空字符串")
    policy["alt_declaration"] = declaration

    labels = policy["alt_declaration_fields"]
    if not isinstance(labels, dict):
        raise ValueError("policy.alt_declaration_fields 必须为对象")
    merged_labels = dict(POLICY_DEFAULTS["alt_declaration_fields"])
    unknown_labels = set(labels) - set(merged_labels)
    if unknown_labels:
        raise ValueError(f"policy.alt_declaration_fields 含未知键：{'、'.join(sorted(unknown_labels))}")
    merged_labels.update(labels)
    if not all(isinstance(label, str) and label.strip() for label in merged_labels.values()):
        raise ValueError("policy.alt_declaration_fields 的值必须为非空字符串")
    policy["alt_declaration_fields"] = merged_labels

    return policy

def parse_alt_declaration(policy):
    """解析分支声明的四个字段（作者/锚点/分歧点/差异），缺失或为空时抛 ValueError。"""
    file_path = Path(policy["alt_declaration"])
    labels = policy["alt_declaration_fields"]
    if not file_path.exists():
        raise ValueError(
            f"{file_path} 不存在：{policy['alt_branch_pattern']} 分支必须提供分支声明"
        )
    label_to_key = {label: key for key, label in labels.items()}
    field_pattern = re.compile(
        r"^[-*]?\s*(" + "|".join(re.escape(label) for label in label_to_key) + r")\s*[：:]\s*(.*)$"
    )
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
        match = field_pattern.match(line)
        if match:
            current = label_to_key[match.group(1)]
            fields[current] = match.group(2).strip()
        elif current == "differences":
            fields[current] = fields.get(current, "") + "\n" + line
    missing = [
        labels[key]
        for key in ("author", "anchor", "diverge", "differences")
        if not fields.get(key, "").strip()
    ]
    if missing:
        raise ValueError(f"{file_path} 缺少字段或字段为空：{'、'.join(missing)}")
    return fields

def check_timeline(meta_json, branch, policy):
    """校验 timeline 与当前分支；policy 为 None 时不启用任何项目规则。"""
    timeline = str(meta_json.get("timeline", "") or "").strip()
    if timeline and not DATE_PATTERN.match(timeline):
        raise ValueError(f"meta.json 的 timeline 必须为 YYYY-MM-DD，当前为 {timeline}")

    info = {"timeline": timeline or None, "branch": branch, "author": None, "diverge": None, "differences": None}
    if policy is None or not policy["enforce_timeline"]:
        return info

    if not timeline:
        raise ValueError("已启用 policy.enforce_timeline，但 meta.json 缺少 timeline 字段（格式 YYYY-MM-DD）")

    mainline = policy["mainline"]
    labels = policy["alt_declaration_fields"]
    declaration_file = policy["alt_declaration"]

    if branch is None:
        print("警告：未检测到 Git 分支，跳过时间线锁定校验")
        return info

    if branch in policy["main_branches"]:
        if timeline != mainline:
            raise ValueError(
                f"主线 {branch} 的 timeline 必须为 {mainline}，当前为 {timeline}；"
                f"如需其他时间点，请新建 {policy['alt_branch_pattern']} 分支或 fork"
            )
        return info

    pattern_segments = policy["alt_branch_pattern"].split("/")
    prefix = pattern_segments[0] + "/"
    if branch.startswith(prefix):
        values = {}
        branch_segments = branch.split("/")
        if len(branch_segments) != len(pattern_segments):
            raise ValueError(f"分支必须命名为 {policy['alt_branch_pattern']}，当前为 {branch}")
        for expected, actual in zip(pattern_segments, branch_segments):
            if expected.startswith("<") and expected.endswith(">"):
                if not actual.strip():
                    raise ValueError(f"分支必须命名为 {policy['alt_branch_pattern']}，当前为 {branch}")
                values[expected[1:-1]] = actual
            elif expected != actual:
                raise ValueError(f"分支必须命名为 {policy['alt_branch_pattern']}，当前为 {branch}")

        if timeline == mainline:
            raise ValueError(f"alt 分支的时间线不得与主线相同（{mainline}）")

        declaration = parse_alt_declaration(policy)
        if declaration["anchor"] != timeline:
            raise ValueError(
                f"{declaration_file} 的{labels['anchor']}（{declaration['anchor']}）"
                f"必须与 meta.json 的 timeline（{timeline}）一致"
            )
        if not DATE_PATTERN.match(declaration["diverge"]):
            raise ValueError(f"{declaration_file} 的{labels['diverge']}必须为 YYYY-MM-DD，当前为 {declaration['diverge']}")
        if declaration["diverge"] > timeline:
            raise ValueError(f"{declaration_file} 的{labels['diverge']}不得晚于{labels['anchor']}")
        if values["author"].lower() not in declaration["author"].lower():
            print(f"警告：分支名中的作者 {values['author']} 未出现在 {declaration_file} 的“{labels['author']}”字段中")

        return {
            "timeline": timeline,
            "branch": branch,
            "author": declaration["author"],
            "diverge": declaration["diverge"],
            "differences": declaration["differences"].strip(),
        }

    print(f"提示：当前分支 {branch} 既不是主线也不是 {policy['alt_branch_pattern']}，跳过时间线锁定校验")
    return info

def read_markdown_lines(file_path):
    """读取 Markdown 文件的所有行；后缀不对或文件不存在时抛 ValueError。"""
    if file_path.suffix.lower() != ".md":
        raise ValueError(f"{file_path} 不是 Markdown 文件（仅支持 .md）")
    if not file_path.exists():
        raise ValueError(f"{file_path} 不存在")
    return file_path.read_text(encoding = "utf-8").splitlines()

def strip_blank_edges(lines):
    """去掉首尾的空行。"""
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines

def extract_section(lines, section, file_path):
    """取出指定标题下的内容（不含标题行），返回 (标题, 正文行)。"""
    start = None
    level = 0
    title = section
    for index, line in enumerate(lines):
        match = HEADING_PATTERN.match(line)
        if match and match.group(2).strip() == section:
            start = index + 1
            level = len(match.group(1))
            title = match.group(2).strip()
            break
    if start is None:
        raise ValueError(f"{file_path} 中找不到小节“{section}”")
    body = []
    for line in lines[start:]:
        match = HEADING_PATTERN.match(line)
        if match and len(match.group(1)) <= level:
            break
        body.append(line)
    return title, strip_blank_edges(body)

def normalize_extend(entries):
    """校验并规范化 extend 字段，返回条目列表。"""
    if not isinstance(entries, list):
        raise ValueError("extend 字段的值必须为数组")
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("extend 的数组内元素必须均为对象")
        if "value" not in entry:
            raise ValueError("extend 条目缺少 value 字段")
        value = entry["value"]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("extend 条目的 value 必须为非空字符串")
        section = entry.get("section")
        if section is not None and (not isinstance(section, str) or not section.strip()):
            raise ValueError("extend 条目的 section 必须为非空字符串")
        position = entry.get("position", "after")
        if position not in ("before", "after"):
            raise ValueError("extend 条目的 position 只能为 before 或 after")
        normalized.append({"value": value.strip(), "section": section, "position": position})
    return normalized

def join_label(label, value):
    """拼接“字段名 + 值”；ASCII 字段名用 ": "，其余用全角冒号。"""
    separator = ": " if all(ord(char) < 128 for char in label) else "："
    return label + separator + value

def render_extend_entry(entry):
    """把单个 extend 条目渲染为打包行。"""
    value = entry["value"]
    section = entry["section"]
    title = None

    if value.startswith("text:"):
        if not section:
            raise ValueError("extend 的内联文本（text:）必须提供 section 字段作为标题")
        title = section.strip()
        body = strip_blank_edges(value[len("text:"):].splitlines())
    elif "::" in value:
        file_name, source_section = value.split("::", 1)
        file_path = Path(file_name.strip())
        title, body = extract_section(read_markdown_lines(file_path), source_section.strip(), file_path)
        if section:
            title = section.strip()
    else:
        file_path = Path(value)
        body = read_markdown_lines(file_path)
        if body:
            match = HEADING_PATTERN.match(body[0])
            if match:
                title = section.strip() if section else match.group(2).strip()
                body = body[1:]
        if not title:
            title = section.strip() if section else file_path.stem
        body = strip_blank_edges(body)

    rendered = []
    if title:
        rendered.append("## " + title)
        rendered.append("")
    for line in body:
        rendered.append("#" + line if line.startswith("#") else line)
    rendered.append("")
    return rendered

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

        # 读取可选策略（未声明时不启用任何项目规则）
        policy = load_policy(meta_json)
        timeline_info = check_timeline(meta_json, get_branch(), policy)

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

        # 解析 extend（附加到打包结果的内容）
        extend_entries = normalize_extend(meta_json.get("extend", []))
        
        # 打包文件
        packaged_title = project_title_version
        if timeline_info["timeline"]:
            packaged_title += " · 时间线 " + timeline_info["timeline"]
        if timeline_info["author"]:
            packaged_title += (
                " · 分支 " + timeline_info["branch"]
                + " · 作者 " + timeline_info["author"]
                + " · 分歧点 " + timeline_info["diverge"]
            )
        packaged_lines = ["# " + packaged_title, ""]

        for entry in extend_entries:
            if entry["position"] == "before":
                packaged_lines += render_extend_entry(entry)

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

        for entry in extend_entries:
            if entry["position"] == "after":
                packaged_lines += render_extend_entry(entry)

        # alt 分支自动附加“与主线的差异”
        if timeline_info["differences"]:
            packaged_lines += render_extend_entry({
                "value": "text:"
                    + join_label(policy["alt_declaration_fields"]["author"], timeline_info["author"]) + "\n\n"
                    + join_label(policy["alt_declaration_fields"]["anchor"], timeline_info["timeline"]) + "\n\n"
                    + join_label(policy["alt_declaration_fields"]["diverge"], timeline_info["diverge"]) + "\n\n"
                    + timeline_info["differences"],
                "section": policy["alt_diff_section"],
                "position": "after",
            })

        packaged_file_path = Path("packaged_file.md").resolve()
        packaged_text = "\n".join(packaged_lines) + "\n"
        packaged_text += "（本文件由 text_packager v" + TOOL_VERSION + " 自动生成，请勿手工修改）" + "\n"
        packaged_text += "（文档结束）" + "\n"

        # 正文未变化时保留原有生成时间，避免每次运行都产生无意义的时间戳差异
        unchanged = False
        if packaged_file_path.exists():
            old_lines = packaged_file_path.read_text(encoding = "utf-8").splitlines()
            old_body = "\n".join(old_lines[:-1]).rstrip("\n") if old_lines else ""
            unchanged = old_body == packaged_text.rstrip("\n")

        meta_file.close()

        if unchanged:
            print(f"内容未变化，未更新 {packaged_file_path}")
        else:
            packaged_file = open(packaged_file_path, "w", encoding = "utf-8")
            packaged_file.write(packaged_text + "\n" + time_text + "\n")
            packaged_file.close()
            print(f"成功打包为 {packaged_file_path}（text_packager v{TOOL_VERSION}）")
    except FileNotFoundError:
        raise FileNotFoundError("请在本目录添加 meta.json")
