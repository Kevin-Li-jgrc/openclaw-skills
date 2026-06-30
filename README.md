# OpenClaw Skills / OpenClaw 技能库

Reusable OpenClaw skills from my local agent setup.

这个仓库用于公开整理我本地 OpenClaw Agent 使用的可复用 skills，方便后续安装、同步和迭代。

## Skills / 技能列表

- `skills/mistral-pdf-ocr`
  - EN: Run Mistral OCR on scanned PDFs and generate Markdown, JSON, and searchable PDFs with preserved page images.
  - 中文：使用 Mistral OCR 识别扫描版 PDF，并生成 Markdown、JSON，以及保留原页面图像的可搜索 PDF。
- `skills/vgage-technical-agreement-extractor`
  - EN: Extract VGAGE technical agreements into a configured Notion analysis database, with routing safeguards for requirement records versus project-progress pages.
  - 中文：将 VGAGE 技术协议抽取为需求分析记录，并通过路由规则区分“项目需求分析库”和“项目进度页”。
- `skills/vgage-project-progress`
  - EN: Update VGAGE weekly project progress from PPT files, manage focused projects, and link progress reminders with ECM-style folder monitoring.
  - 中文：从项目例会 PPT 更新 VGAGE 项目进度，管理关注项目，并联动 ECM 类文件夹监控提醒。

## Repository Structure / 仓库结构

```text
skills/
  mistral-pdf-ocr/
    SKILL.md
    scripts/
  vgage-technical-agreement-extractor/
    SKILL.md
  vgage-project-progress/
    SKILL.md
```

Each skill lives in its own folder under `skills/`.

每个 skill 都放在 `skills/` 下的独立目录中。

## Safety / 安全约定

This repository is intended for public skill code only.

本仓库只用于公开可复用的 skill 代码和说明。

- EN: Do not commit API keys, tokens, secrets, private memory files, or OCR output files.
- 中文：不要提交 API Key、token、密钥、私人记忆文件或 OCR 输出文件。
- EN: Keep generated files under local `temp/` or another ignored output directory.
- 中文：生成的临时文件应保存在本地 `temp/` 或其他已忽略的输出目录中。
- EN: Review each skill before publishing it here.
- 中文：每次发布新 skill 前，都要先做一次敏感信息和安全审查。

## License / 许可证

No license has been selected yet.

暂未指定开源许可证。
