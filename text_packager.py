# text_packager.py
# 111 lines of code, including annotations and blank lines
# Time: 2026-06-19T15:00:00+08:00
# Copyright (c) 2026 MarchBeta2087
# SPDX-License-Identifier: MIT

import json
from datetime import datetime
import pytz
from tzlocal import get_localzone
from pathlib import Path

tz = pytz.timezone(get_localzone().key)
time_text = datetime.now(tz).isoformat(timespec='seconds')

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
        packaged_lines = ["# " + project_title_version, ""]
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
        packaged_file.write("（文档结束）" + "\n\n" + time_text + "\n")

        meta_file.close()
        packaged_file.close()

        print(f"成功打包为 {packaged_file_path}")
    except FileNotFoundError:
        raise FileNotFoundError("请在本目录添加 meta.json")
