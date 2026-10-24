# text_packager.py 使用文档

## 简介

`text_packager.py` 是一个轻量级文档打包工具，用于将多个 Markdown（`.md`）文件按照指定的目录结构合并为一份完整的 Markdown 文档。它特别适合用于整理项目文档、人物设定集、技术手册等需要版本化聚合输出的场景。

程序通过读取 `meta.json` 配置文件，递归遍历文件树，自动调整各级标题的层级深度，最终生成一份结构清晰、便于分享或导出的单一文档。

## 特性

- 支持任意层级嵌套的目录结构。
- 自动根据目录深度调整 Markdown 标题级别（`#` \~ `######`）。
- 保留原始文件内容的完整性，仅调整标题的缩进。
- 输出文件带有生成时间戳（基于本地时区）。
- 错误提示明确，配置格式错误或文件缺失时能快速定位问题。

## 系统要求

### Python 版本

Python 3.6 及以上（推荐 Python 3.8+）。

### 操作系统

- 跨平台：Windows 7 及以上版本、macOS、Linux 均可运行。

### 第三方依赖

需要安装以下两个 Python 库：

- `pytz`：时区处理
- `tzlocal`：自动获取系统本地时区

安装命令：

```bash
pip install pytz tzlocal
```

其余使用的库（`json`、`datetime`、`pathlib`）均为 Python 标准库，无需额外安装。

## 快速开始

### 1. 准备文件结构

在运行脚本的目录下，准备好：

- `meta.json`：配置文件（必须存在）。
- 所有需要打包的 `.md` 文件，其路径与 `meta.json` 中 `children` 的定义一致。

### 2. 运行脚本

```bash
python text_packager.py
```

### 3. 输出结果

若一切顺利，将在当前目录生成 `packaged_file.md`，内容即为打包后的完整文档。

## meta.json 配置格式

`meta.json` 是程序的唯一输入配置，其结构必须严格遵循以下规范：

```json
{
  "title": "项目标题",
  "version_tag": "版本标签",
  "type": "project",
  "children": [
    { "name": "file1.md", "type": "file" },
    {
      "name": "subdir_name",
      "title": "子目录显示标题",
      "type": "directory",
      "children": [
        { "name": "file2.md", "type": "file" },
        { "name": "file3.md", "type": "file" }
      ]
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
| ---- | ---- | ---- | ---- |
| title | string | 是 | 项目主标题，会显示在打包文档的第一行 |
| version_tag | string | 是 | 版本标识，例如 v1.0、v2.0-alpha2 |
| type | string | 是 | 必须为 "project" |
| children | array | 是 | 文件或目录的列表，顺序即为打包文档中的排列顺序 |

#### children 子项

每个子项是一个对象，支持两种类型：

##### 文件类型（type: "file"）

```json
{ "name": "filename.md", "type": "file" }
```

- name：文件名（不含路径），不能包含 / 或 \，文件必须位于当前目录或与 `meta.json` 同级的子目录中。

##### 目录类型（type: "directory"）

```json
{
  "name": "folder_name",
  "title": "章节标题",
  "type": "directory",
  "children": [ ... ]
}
```

- name：目录名，同样不能包含路径分隔符。
- title：在打包文档中显示为该目录的标题（会转换为对应层级的 Markdown 标题）。
- children：该目录下的文件/子目录列表，结构相同。

##### 注意事项

- name 字段只能为单个文件或目录名称，不允许包含路径分隔符（如 `subdir/file.md` 是不合法的）。
- 所有引用的 `.md` 文件必须实际存在，否则程序会报错并中断。
- 目录层级深度理论上不限，但 Markdown 仅支持 6 级标题（######），过深层级可能影响可读性。

## 工作原理

1. 解析 `meta.json`：读取配置，验证必要字段。
2. 递归遍历：根据 children 树，收集所有 `.md` 文件的路径，同时记录每个文件所在的目录深度。
3. 生成打包内容：
   - 首行：`# 项目标题 版本标签`
   - 对每个文件：
     - 如果是目录节点，插入一个该目录的标题（层级 = 目录深度）。
     - 如果是文件，读取其内容，并将其内部所有以 # 开头的行，前面增加对应深度的 #（例如深度为 2，则 # 标题 变为 ### 标题）。
   - 所有原内容逐行保留（去除行尾的 `\r\n`）。
4. 添加文档结束标记：在末尾添加 （文档结束） 和当前本地时间（ISO 格式）。
5. 写入文件：输出为 `packaged_file.md`。

## 示例

假设有以下文件结构：

```
.
├── meta.json
├── intro.md
├── chapters/
│   ├── chapter1.md
│   └── chapter2.md
└── appendix/
    └── notes.md
```

`meta.json` 内容：

```json
{
  "title": "我的项目",
  "version_tag": "v1.0",
  "type": "project",
  "children": [
    { "name": "intro.md", "type": "file" },
    {
      "name": "chapters",
      "title": "核心章节",
      "type": "directory",
      "children": [
        { "name": "chapter1.md", "type": "file" },
        { "name": "chapter2.md", "type": "file" }
      ]
    },
    {
      "name": "appendix",
      "title": "附录",
      "type": "directory",
      "children": [
        { "name": "notes.md", "type": "file" }
      ]
    }
  ]
}
```

运行后生成的 packaged_file.md 结构大致如下：

```
# 我的项目 v1.0

（intro.md 的内容，其一级标题变为 #，二级变为 ## 等）

## 核心章节

（chapter1.md 的内容，其一级标题变为 ##，二级变为 ### 等）

（chapter2.md 的内容，类似）

## 附录

（notes.md 的内容，类似）

（文档结束）

2026-06-19T14:20:15+08:00

```

## 错误处理

程序会对以下情况抛出明确的异常信息：

| 错误情况 | 提示信息示例 |
| -------- | ------------ |
| `meta.json` 不存在 | `请在本目录添加 meta.json` |
| `meta.json` 格式不是合法 JSON | `不符合 JSON 格式规范` |
| 根对象缺少 `title` 或 `version_tag` | `请补充根对象 title 和 version_tag 字段` |
| 根对象 type 不是 "project" 根对象 | `type 的值必须为 project` |
| 子对象缺少 name 或 type | `子对象 name 字段缺失` 等 |
| name 包含 `/` 或 `\` | `name 字段的值不得包含斜杠和反斜杠` |
| 引用的文件不存在 | `[文件名] 不存在` |
| 文件不是 `.md` 后缀 | `仅支持 Markdown 文件（.md）` |

## 作者与维护

本工具由 MarchBeta2087 开发维护。欢迎提交 Issue 或 Pull Request 改进功能。

## 更新日志

- v1.0：初始版本，支持基本打包功能。
