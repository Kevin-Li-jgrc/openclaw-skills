# Boundary Contract

1. Read original VGAGE project files without modifying, deleting, repairing, uploading, or overwriting them.
2. Create output only in a new project-local `VGAGE_REVIEW_YYYYMMDD_HHMMSS/` directory.
3. Exclude every existing `VGAGE_REVIEW_*` directory from inventory, facts, and project hashes.
4. Do not query Kevin-Knowledge, qmd, Notion, the web, or another Skill for runtime rules.
5. Scope is limited to project files, program logic, and program-side interface configuration. Program-side object existence, dangling references, duplicate/conflicting mappings, formula/config consistency, disabled/placeholder configuration, and deterministic state/alarm/reset defects remain in scope.
6. Exclude actual PLC address correctness, physical channel/wiring, sensor sign/direction, COM connection, air pressure, limits, cylinders, motors, workpiece seating, actual safety-device effect, actual cycle, whole-machine interlock, and real PLC/robot/MES/marking communication.
7. Migrated field-verification items are absent from the active catalog and **不输出为 MANUAL_VERIFY、NOT_ASSESSABLE 或附加现场清单**.
8. Require concrete project-file evidence for AI FAIL. Otherwise use `MANUAL_VERIFY` or `NOT_ASSESSABLE` only for retained program-review rules.
9. Treat static review as evidence only. Never state that equipment acceptance has passed.
10. Keep rule updates pending until Kevin explicitly applies a Skill Workshop proposal.
