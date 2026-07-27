---
name: "encrypted-office-reader"
description: "通过Office COM接口读取非标准加密的Excel/Word文档"
---

# Excel/Word 加密文档读取 Skill

## 触发条件

当需要读取文件头为 `0x18 0x1b` 的加密 Office 文档时触发，或 Kevin 说：

- "读取加密Excel" / "读一下这个加密的xlsx"
- "打开这个加密Word" / "读取加密docx"
- 普通工具无法打开某个 `.xlsx` / `.docx` 文件时自动尝试

## 功能概述

读取非标准格式的 Excel 和 Word 文档。这类文档虽然扩展名为 `.xlsx` / `.docx`，但文件头不是标准 ZIP 格式（`PK`），而是 `0x18 0x1b` 开头，普通解压工具无法处理。通过 Microsoft Office COM 接口可以正常打开和读取。

## 依赖

- Windows 操作系统
- Microsoft Excel（读取 `.xlsx` 文件）
- Microsoft Word（读取 `.docx` 文件）
- PowerShell 5.1+

## 工具

### read_encrypted_excel

读取加密的 Excel 文件并输出内容。

**参数：**
- `file_path` (string, required)：Excel 文件路径
- `max_rows` (number, optional)：最大输出行数，默认全部输出
- `format` (string, optional)：输出格式，`text` 或 `json`，默认 `text`

**示例：**
```json
{
  "file_path": "C:\\path\\to\\file.xlsx",
  "max_rows": 50,
  "format": "json"
}
```

### read_encrypted_word

读取加密的 Word 文件并输出内容。

**参数：**
- `file_path` (string, required)：Word 文件路径
- `format` (string, optional)：输出格式，`text` 或 `json`，默认 `text`

**示例：**
```json
{
  "file_path": "C:\\path\\to\\file.docx",
  "format": "text"
}
```

## 脚本

### 命令行入口

`scripts/read-encrypted.ps1` — 独立 PowerShell 脚本，用法：

```powershell
# 读取 Excel
.\scripts\read-encrypted.ps1 -Type excel -FilePath "C:\path\to\file.xlsx" -MaxRows 50

# 读取 Word
.\scripts\read-encrypted.ps1 -Type word -FilePath "C:\path\to\file.docx" -Format json
```

### PowerShell 模块

`Read-EncryptedOffice.psm1` — 可导入模块，提供两个函数：

```powershell
Import-Module .\Read-EncryptedOffice.psm1

# 读取 Excel
Read-EncryptedExcel -FilePath "C:\path\to\file.xlsx" -MaxRows 100

# 读取 Word
Read-EncryptedWord -FilePath "C:\path\to\file.docx"
```

### 使用示例

详见 `examples/example-usage.ps1`。

## 实现原理

使用 PowerShell 调用 Microsoft Office COM 接口：
- Excel：`New-Object -ComObject Excel.Application`
- Word：`New-Object -ComObject Word.Application`

读取完成后自动关闭 Office 应用程序并释放 COM 对象。

## 已知限制

1. **仅 Windows**：依赖 Microsoft Office COM 接口，不支持 macOS / Linux。
2. **需要安装 Office**：必须安装 Microsoft Excel 和/或 Word 桌面版。
3. **首次运行可能弹窗**：Office 安全提示可能需要手动确认。
4. **大文件较慢**：COM 接口逐单元格读取，大文件可能需要较长时间。
