# text_packager.py 使用文档

## 简介

`text_packager.py` 是一个轻量级文档打包工具，用于将多个 Markdown（`.md`）文件按照指定的目录结构合并为一份完整的 Markdown 文档。它特别适合用于整理项目文档、人物设定集、技术手册等需要版本化聚合输出的场景。

程序通过读取 `meta.json` 配置文件，递归遍历文件树，自动调整各级标题的层级深度，最终生成一份结构清晰、便于分享或导出的单一文档。

## 特性

- 支持任意层级嵌套的目录结构。
- 自动根据目录深度调整 Markdown 标题级别（`#` \~ `######`）。
- 保留原始文件内容的完整性，仅调整标题的缩进。
- 输出文件带有生成时间戳（基于本地时区）；正文未变化时不更新生成时间。
- 支持 `extend` 字段：把额外文件、某一小节或内联文本附加到打包结果，不必手改输出文件。
- 可选的项目策略（`policy`）：启用后校验 `timeline` 与 Git 分支，并在 `alt` 分支自动附加“与主线的差异”；不写 `policy` 时不做任何校验。
- 工具版本与项目版本相互独立：工具版本见脚本顶部的 `TOOL_VERSION`、控制台输出与输出文件末尾；项目版本仍是 `meta.json` 的 `version_tag`。
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
- 所有需要打包的 `.md` 文件，其路径与 `meta.json` 中 `children`、`extend` 的定义一致。

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
  "timeline": "2033-11-13",
  "author": "作者名",
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
  ],
  "extend": [
    { "value": "README.md::时间线", "section": "时间线说明" }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
| ---- | ---- | ---- | ---- |
| title | string | 是 | 项目主标题，会显示在打包文档的第一行 |
| version_tag | string | 是 | 版本标识，例如 v1.0、v2.0-alpha2 |
| timeline | string | 否 | 设定的“现在”，格式 `YYYY-MM-DD`；启用 `policy.enforce_timeline` 时必填 |
| policy | object | 否 | 项目自己的时间线与分支规矩，见下文；不写则只做打包 |
| author | string | 否 | 维护者署名，仅用于 `alt` 分支的标题展示 |
| type | string | 是 | 必须为 "project" |
| children | array | 是 | 文件或目录的列表，顺序即为打包文档中的排列顺序 |
| extend | array | 否 | `children` 之外要附加的内容，见下文 |

> 未声明 `policy` 时，`timeline` 只用于标题展示；时间线锁定、分支命名与声明文件校验全部关闭。

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

## policy 策略（可选）

`policy` 用来声明项目自己的规矩（时间线与分支）。**不写这个字段时，脚本只做打包**：不校验分支、不要求声明文件、不附加差异节，`timeline` 仅用于标题。

```json
"policy": {
  "enforce_timeline": true,
  "mainline": "2033-11-13"
}
```

| 字段 | 默认值 | 说明 |
| ---- | ------ | ---- |
| enforce_timeline | `true` | 总开关；为 `false` 时等价于不写 `policy` |
| mainline | 无（启用时必填） | 主线的时间线日期 |
| main_branches | `["main", "master"]` | 视为主线的分支名 |
| alt_branch_pattern | `"alt/<author>/<diverge>"` | 分支命名规则，`<...>` 为占位段 |
| alt_declaration | `"ALT.md"` | 分支声明文件名（位于仓库根目录） |
| alt_declaration_fields | 作者 / 锚点 / 分歧点 / 与主线差异 | 声明文件字段名，按 `author`、`anchor`、`diverge`、`differences` 四个角色配置 |
| alt_diff_section | `"与主线的差异"` | 自动附加小节的标题 |

启用后的行为：

- 主线分支上：`timeline` 必须等于 `mainline`，否则报错；
- `alt_branch_pattern` 形状的分支上：`timeline` 不得等于 `mainline`，声明文件四个字段齐全，`anchor` 等于 `timeline`，`diverge` 不晚于 `anchor`；打包时自动附加差异小节；
- 其他分支：跳过校验并给出提示。

`policy` 中出现未知字段会直接报错，防止拼写错误导致规则静默失效。

## extend 附加内容

`extend` 用于把 `children` 之外的内容附加到打包结果，避免手工修改 `packaged_file.md`。

```json
"extend": [
  { "value": "README.md::时间线", "section": "时间线说明" },
  { "value": "MANIFEST.md" },
  { "value": "text:本文件由脚本生成。", "section": "说明", "position": "before" }
]
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
| ---- | ---- | ---- | ---- |
| value | string | 是 | 内容来源，三种形式见下 |
| section | string | 否 | 输出中该节的标题；`text:` 形式必填 |
| position | string | 否 | `before` 或 `after`，默认为 `after` |

`value` 的三种形式：

1. `路径::小节标题`：取该 Markdown 文件中指定标题下的内容（不含标题行），`section` 可覆盖输出标题。
2. `路径`：整篇引入，文件首个标题会作为该节标题，`section` 可覆盖。
3. `text:...`：内联文本，必须提供 `section`。

正文中的标题会统一降一级（`##` → `###`），与 `children` 中文件的处理方式一致。小节按标题文字精确匹配，取到下一个同级或更高级标题为止；找不到文件或小节时直接报错。

在 `alt/*` 分支上，脚本还会自动追加一节“与主线的差异”，内容取自 `ALT.md`，无需手写。

## 工作原理

1. 解析 `meta.json`：读取配置，验证必要字段；若有 `policy`，按策略校验 `timeline` 与当前 Git 分支。
2. 递归遍历：根据 children 树，收集所有 `.md` 文件的路径，同时记录每个文件所在的目录深度。
3. 生成打包内容：
   - 首行：`# 项目标题 版本标签 · 时间线 <timeline>`（`alt` 分支还会附带分支名、作者与分歧点）
   - 对每个文件：
     - 如果是目录节点，插入一个该目录的标题（层级 = 目录深度）。
     - 如果是文件，读取其内容，并将其内部所有以 # 开头的行，前面增加对应深度的 #（例如深度为 2，则 # 标题 变为 ### 标题）。
   - 所有原内容逐行保留（去除行尾的 `\r\n`）。
4. 附加 `extend` 内容：按 `position` 插入 `before` 或 `after` 的位置；`alt` 分支再追加“与主线的差异”。
5. 添加文档结束标记：在末尾添加自动生成提示、（文档结束） 和当前本地时间（ISO 格式）；若正文与已有输出一致，则保留原有生成时间，不重复写入。
6. 写入文件：输出为 `packaged_file.md`。

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
| `timeline` 格式错误 | `meta.json 的 timeline 必须为 YYYY-MM-DD……` |
| 启用策略但缺少 `timeline` | `已启用 policy.enforce_timeline，但 meta.json 缺少 timeline 字段……` |
| 主线时间线与 `mainline` 不符 | `主线 main 的 timeline 必须为 2033-11-13……` |
| `policy` 含未知字段 | `policy 含未知字段：enforce_timline` |
| 分支命名不符 | `分支必须命名为 alt/<author>/<diverge>，当前为……` |
| `alt` 分支缺少声明文件 | `ALT.md 不存在：alt/<author>/<diverge> 分支必须提供分支声明` |
| `extend` 条目不合法 | `extend 条目缺少 value 字段` 等 |
| `extend` 引用的小节不存在 | `README.md 中找不到小节“时间线”` |

## 作者与维护

本工具由 MarchBeta2087 开发维护。欢迎提交 Issue 或 Pull Request 改进功能。

## 更新日志

- v1.1：新增 `extend` 附加内容；时间线与分支规则改为可选的 `policy` 策略（不写则不校验，分支命名、声明文件名与字段名均可配置）；新增独立的 `TOOL_VERSION`，与项目版本、时间线区分；正文未变化时不更新生成时间。
- v1.0：初始版本，支持基本打包功能。
