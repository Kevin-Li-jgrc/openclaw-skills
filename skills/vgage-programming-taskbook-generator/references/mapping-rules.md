# VGAGE 编程任务书映射规则

Use these rules to map requirements into VGAGE files and task groups.

## Three-layer to file mapping

| Layer | Requirement examples | Primary targets |
| --- | --- | --- |
| 硬件交互层 | PLC, IO, sensor channel, serial, IPPort, barcode, RTG trigger | `IO.xml`, `VGA.xml` Probe, `CodeModule.vgs`, Form XML |
| 检测参数层 | Probe, Measurement, Nominal, tolerance, formula, dynamic sampling | `VGA.xml`, `CodeModule.vgs`, Form XML, `Q-DAS.xml`, `SPC.xml` |
| 客户定制功能层 | MES, marking, anti-duplicate, report, permission, compensation, Q-DAS/SPC | `CodeModule.vgs`, config files, Form XML, `Screens.xml`, `Q-DAS.xml`, `SPC.xml` |

## Common target files

- `VGA.xml`: Part, ReadyToGage, Probe, Measurement, ToolComp, Nominal, tolerance, formulas.
- `CodeModule.vgs`: shared formulas, event glue, cautious hardware/data logic, helper calls.
- `IO.xml`: PLC/IO/Tag/serial/IPPort object definitions and addresses.
- Form XML: buttons, text boxes, manual triggers, display and operator workflow.
- `Screens.xml`: screen entry and UI composition.
- `Settings.config` / `.config` / `.ini`: site parameters, MES endpoints, toggles, cache paths.
- `Q-DAS.xml`: Q-DAS field and export configuration.
- `SPC.xml`: SPC output and statistical behavior.

## Status labels

- `可草拟`: can be drafted from evidence but still requires review.
- `可直接执行`: evidence is explicit and risk is bounded.
- `需现场确认`: high-risk field or ambiguity exists.
- `禁止自动判断`: missing direction/sign/channel/timing/address/field semantics.
- `建议试验副本`: likely to affect startup, compile, event source, hardware IO, or data upload.

## Mapping cautions

- If Measurement has a `Nominal`, formula usually returns deviation such as `actual - Me.Nominal`; do not duplicate nominal inside the final value unless the project pattern proves it.
- Measurement formulas that reference Probe values must have matching Measurement Probe binding.
- Computed Probes that reference other Probes must have correct Dependencies.
- Direct channel Probes usually keep Dependencies empty.
- Marking is customer-specific first and hardware interaction second.
- MES/HTTP/file-cache logic may require helper or Form-based implementation if `CodeModule.vgs` event hooks are risky in that project.
- DWG-derived formulas are drafts until direction, sign, channel, and RTG timing are confirmed.
