---
name: vgage-project-progress
description: Use when updating VGAGE weekly project progress from PPT files, managing focused project numbers, or linking progress status with ECM-style engineering file monitoring.
---

# VGAGE Project Progress

Use this skill for VGAGE weekly project meeting PPT updates, focused-project tracking, and ECM-style Mechanical folder follow-up linkage.

This public version is a reusable template. Replace the placeholders below with your own Notion database, scripts, and folder-monitor configuration before use.

## Canonical Files

- Notion database: `VGAGE项目进度`, database id `<VGAGE_PROJECT_PROGRESS_DATABASE_ID>`
- PPT updater / focus manager: `<WORKSPACE>/scripts/vgage_project_progress.py`
- Focus config shared with monitor cron: `<WORKSPACE>/data/vgage-focused-projects.json`
- ECM-style folder monitor: `<WORKSPACE>/scripts/ecm_folder_monitor.py`
- ECM-style cron runner: `<WORKSPACE>/scripts/ecm_folder_monitor_cron_runner.sh`

## Critical Rule: PPT Status Source

For the weekly meeting PPT, status must come from slide 3 quadrant table coordinates, not from extracted linear text.

Slide 3 layout:

- left-top table = `装配`
- right-top table = `装配·制造·采购`
- left-bottom table = `制造·采购`
- right-bottom table = `设计`

If slide 3 no longer has exactly these four quadrant tables, stop and ask the operator. Do not guess.

Detail slides may enrich `本周关注点` / `风险/阻塞` / `节点状态说明`, but must not override the slide-3 status.

## Project Number vs Equipment Number

- `项目号` is usually a 4- or 5-digit project number.
- `设备号` is typically `项目号 + 3-digit sequence`.
- Monitoring and Notion focused-project tracking should use the 4/5-digit project number as the primary key.
- If a 7/8-digit equipment number is supplied, derive the project number by removing the last 3 digits before updating focus config.

Special cross-company numbering:

- Sometimes two project numbers from different company systems refer to the same equipment.
- Treat the primary project number as the focus entry and store the other number under `ecmAliases`.
- ECM-style project folders may include both project number and customer/project description, not just the pure project number.
- Folder lookup should try exact match first, then project-number prefix / contained-number matching.
- If multiple candidates are found, report them for operator confirmation instead of guessing.

## Update Notion From a New PPT

```bash
cd <WORKSPACE>
python3 scripts/vgage_project_progress.py update-ppt /path/to/项目例会材料YYYY.MM.DD.pptx --notify
```

What the script should do:

1. Parse slide 3 by table coordinates.
2. Update or create Notion rows by project number + client + device.
3. Write structured change markers so the Notion table can show what moved this week.
4. Update focus config snapshot for focused projects.
5. Notify if a focused project transitions from manufacturing-only (`制造·采购`) to an assembly-related node (`装配` or `装配·制造·采购`).

Change-marker fields in Notion:

- `变更标记`: `新项目` / `阶段推进` / `阶段回退` / `节点变化` / `无变化`.
- `变更摘要`: short human-readable diff, for example `制造·采购 -> 装配`.
- `上次状态`: the status read from the row before the update.
- `变化时间`: set only when the marker is not `无变化`.

The Notion database also keeps the current baseline rows as `无变化`. The next PPT update should overwrite those fields based on the real before/after comparison.

Time-node changes are not inferred from slide 3 alone. Only mark `时间节点变化` after a stable date source is parsed or the operator explicitly supplies the node change.

Before first use on a new PPT layout, run:

```bash
python3 scripts/vgage_project_progress.py update-ppt /path/to/file.pptx --dry-run
```

## Add a Focused Project

When a project number should be followed:

```bash
python3 scripts/vgage_project_progress.py add-focus 12345 --label "12345｜客户｜设备"
```

For a same-equipment cross-company project number:

```bash
python3 scripts/vgage_project_progress.py add-focus 12345 --ecm-alias 6789
```

If an assembly completion node is known:

```bash
python3 scripts/vgage_project_progress.py add-focus 12345 --assembly-due 2026-06-20
```

Effects:

- Adds the project to `data/vgage-focused-projects.json`.
- The ECM-style cron reads this shared list automatically.
- `--ecm-alias` adds additional project-folder numbers to monitor for the same focused equipment.
- Project number must be validated before writing config.
- Focus config writes should be atomic to avoid corrupting the cron input file.
- If the project is in an assembly-related PPT node, the ECM-style cron includes a daily reminder to follow current assembly status.
- If `assemblyDue` is set, the cron reminds at D-7, D-3, D-1, and D0 to complete VGAGE Pro program writing before the assembly node.

## ECM Linkage Behavior

The ECM-style Mechanical cron still monitors server-side Mechanical folder additions. This skill only adds VGAGE progress reminders into the same notification flow.

Notification distinction:

- `ECM Mechanical 新增`: server folder changed.
- `VGAGE 关注项目提醒`: focused project is in assembly stage and/or VGAGE Pro program deadline is near.

Do not download, upload, modify, or delete ECM files unless the operator explicitly asks for that separate action.

Robustness rules:

- A new focused project that cannot be found on ECM is reported as `待定位`; the cron must continue checking other projects.
- A malformed focused project entry is skipped and reported as a config warning; it must not fail the cron.
- If the shared focus config file is unreadable/corrupt, ECM cron falls back to default projects and reports the config warning.
- Only ECM login/global server failure should fail the cron and trigger failure alerts.

## Verification Checklist

After changing scripts or config:

```bash
python3 -m py_compile scripts/vgage_project_progress.py scripts/ecm_folder_monitor.py
python3 scripts/vgage_project_progress.py list-focus
python3 scripts/vgage_project_progress.py update-ppt /path/to/latest.pptx --dry-run
python3 scripts/ecm_folder_monitor.py --json --baseline-no-alert
```

Avoid running the cron runner with `--notify-success` during tests unless the operator expects a test notification.
