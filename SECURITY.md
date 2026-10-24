# 安全策略 (Security Policy)

## 适用的工具范围

本安全策略主要适用于仓库内的 Python 打包工具链：
- `text_packager.py`

| 工具版本 | 是否维护支持 |
| :--- | :--- |
| v1.2 | :white_check_mark: 是 |
| < v1.2 | :x: 否 |

## 报告安全漏洞

如果你在 `text_packager.py` 的路径解析、命令执行（`subprocess`）或文件处理过程中发现了安全隐患（例如路径遍历漏洞）：

1. **请勿**在公开的 Issue 中披露漏洞。
2. 请通过 GitHub 仓库的 **Security Advisories**（“Report a vulnerability” 按钮）提交私密安全报告，或通过邮件联系维护者。
3. 我们会在确认后尽快修复并发布新补丁。
