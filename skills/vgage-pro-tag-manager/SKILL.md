---
name: "vgage-pro-tag-manager"
description: "统一 VGAGE User Tag 的有效 Text、备注、默认值与安全迁移。"
---

# VGAGE Pro Tag Manager

用于三个 VGAGE Worker 新建、修改和验证 `IO.xml/Tags`。本 Skill 是 User Tag 字段职责、默认值归属、旧项目迁移、HMI/PLC 引用及交付验收的统一规则。

## 一、适用范围与默认契约

适用于：

- 新建 VGAGE Pro User Tag；
- 修改由 Worker 创建或扩展的 Tag；
- 将旧项目中默认值从 `Text` / `Description` 迁移到运行时 `.Value`；
- 校验 Tag、Devices、PLC 映射与 HMI 绑定；
- 为项目建立可回归的 Tag 契约测试。

对三个 Worker 今后新建的 User Tag，强制使用：

```text
XML 元素名 = Name
Text 的有效值 = Name
Description = 中文用途备注
业务值 / 默认值 / 运行状态 = Value
```

示例：

```xml
<MesServerIP Type="String"
 Name="MesServerIP"
 Text="MesServerIP"
 Description="MES服务器IP" />

<HmiCmdReset Type="Boolean"
 Name="HmiCmdReset"
 Text="HmiCmdReset"
 Description="复位命令" />
```

创建或外部编辑时应显式写入 `Text="Name"`；但 VGAGE Pro 保存时可能省略与 `Name` 相同的显式 `Text` 属性。读取和审核时，缺失 `Text` 的有效值必须按 `Name` 解释；若显式存在，必须精确等于 `Name`。不得把中文说明、默认值、枚举列表、IP、端口、URL、路径、产品型号或运行状态保存在 `Text` 或 `Description`。

## 二、字段职责

| 字段 | 统一规则 |
|---|---|
| XML 元素名 | 必须与 `Name` 完全一致 |
| `Name` | 脚本、控件、PLC 映射和引用使用的稳定标识 |
| `Text` | 有效值必须精确等于 `Name`：可显式为 `Name`，也可由 VGAGE 保存时省略；缺失按 `Name` 解释，且不得作为业务值读取 |
| `Description` | 只写非空中文用途备注，不写默认值或枚举 |
| `Value` | 保存默认值、配置值和运行值 |
| `Type` | 由业务类型决定，不得为满足命名格式而改变 |
| `Equation` | 只用于明确的 Scripted 计算，不因 Text 迁移改变 |

新代码禁止读取 `Tag.Text` 作为业务值。字符串比较、拼接、解析、URL、路径和 MES 请求统一读取 `Tag.Value`。

## 三、Tag 分类与默认值归属

修改前必须把目标 Tag 分为四类，并建立清单：

| 分类 | 典型对象 | 默认值规则 |
|---|---|---|
| 界面参数 | 模式、阈值、A1/B1、可编辑配置 | 由所属 Form 初始化代码写入 `.Value` |
| 启动配置 | 无专属编辑界面的 MES/API/路径配置 | 由生产主界面调用一次性初始化函数 |
| 硬件/运行态 | PLC 输入输出、HMI 命令/状态、扫码结果 | 不强制写默认值，由外部动作或运行流程驱动 |
| 公式态 | `Scripted=True` 的 Equation Tag | 不写默认值，由 Equation 计算 |

系统 Tag、项目原有公共 Tag 和未授权 Tag 不得为了形式统一而自动修改。

## 四、界面默认值规则

有默认值的 Tag 必须在对应界面或明确的启动事件中用代码赋给 `.Value`。

### 4.1 有 `SaveSelection` 的控件

- 已保存控件值优先。
- 仅控件为空时填默认值。
- 初始化完成后，由同步函数将控件内容写入 Tag `.Value`。
- 重复打开界面不得覆盖已保存值。
- 静态 Form XML 不再同时保存同一默认值，避免双重来源。

示例：

```vb
Private Sub EnsureParameterDefaults()
    ' SaveSelection 已恢复的值优先；仅空值使用项目默认值。
    If Combo_Source.Text.Trim = "" Then Combo_Source.Text = "固定值"
    If Text_A1.Text.Trim = "" Then Text_A1.Text = "23"
    If Text_B1.Text.Trim = "" Then Text_B1.Text = "0"
End Sub

Private Sub SyncParametersToTags()
    SourceMode.Value = Combo_Source.Text
    A1Fixed01.Value = ParseDouble(Text_A1.Text, A1Fixed01.Value)
    B1Mock01.Value = ParseDouble(Text_B1.Text, B1Mock01.Value)
End Sub
```

对于 CheckBox，界面控件是持久化来源：初始化/显示时将 `Checked` 同步到 Tag `.Value`，不得在随后事件中强制改回默认值。

### 4.2 无持久化控件的配置

- 使用一次性初始化函数。
- 仅在 `.Value` 为空、未初始化或等于 Tag.Name 占位值时写入默认值。
- 使用私有布尔标志防止同一运行周期重复执行。
- 由生产主界面的 `VGA.Initialize` 调用一次。
- 禁止在 `Refresh`、`AfterUpdate`、定时器或其他周期事件中调用。

示例：

```vb
Private DefaultsInitialized As Boolean = False

Public Sub EnsureDefaultsInitialized()
    If DefaultsInitialized Then Exit Sub
    DefaultsInitialized = True

    If SafeTrim(MesServerIP.Value) = "" OrElse _
       SafeTrim(MesServerIP.Value) = "MesServerIP" Then
        MesServerIP.Value = "127.0.0.1"
    End If
End Sub
```

### 4.3 注释要求

默认值初始化代码必须写中文备注，说明：

- 默认值由哪个界面/事件负责；
- 已保存值是否优先；
- 为什么只初始化一次；
- 哪些 Tag 由 PLC、HMI、Equation 或扫码流程驱动，因此不写默认值。

## 五、新建 Tag 流程

1. 读取当前项目的 `IO.xml`、相关 Form、`CodeModule.vgs`、`Screens.xml` 和 `Settings.config`。
2. 用三层框架确认 Tag 属于硬件交互、检测参数还是客户定制功能。
3. 确认用途、`Type`、数据方向、读写方、默认值和默认值所属事件面。
4. 检查名称合法性、大小写唯一性及与 Probe、Measurement、控件、VB 关键字的冲突。
5. 创建或外部编辑时令 XML 元素名、`Name`、显式 `Text` 完全一致；保存后若 VGAGE 省略 `Text`，审核按缺失即 `Name` 的有效值语义验证。
6. `Description` 写准确中文用途；命令与状态反馈必须区分。
7. 默认值写入对应 Form/启动代码的 `.Value`，不得写入 `Text` 或 `Description`。
8. PLC 映射中的 `VgaTag` 必须与 `Name` 一致；不得猜测 PLC 地址、读写方向或 Bit 位号。
9. `Button.DestTag`、`Led.SourceTag` 等引用必须能解析到对应 Tag。
10. 只修改项目副本；写入前创建不覆盖的版本化备份。

## 六、旧项目受控迁移流程

本规则不授权对历史项目全部 Tag 自动批量改写。迁移必须先明确目标集合。

### 6.1 盘点

对每个目标记录：

- XML 元素名、`Name`、`Type`、`Text`、`Description`；
- `.Text`、`.Value`、`.Description` 的全项目引用；
- 默认值、来源界面、保存方式和重置语义；
- PLC 地址、`ReadWriteMode`、`VgaTag`；
- HMI `DestTag`、`SourceTag`；
- 是否由 PLC、HMI、Equation、扫码或 MES 流程驱动。

### 6.2 迁移顺序

1. 先把目标业务读取从 `Tag.Text` 改为 `Tag.Value`。
2. 再把默认值迁移到对应 Form 或一次性启动函数。
3. 再将目标显式 `Text` 改为 `Name`；若后续 VGAGE 保存省略该属性，按缺失即 `Name` 的有效值语义验收。
4. 将 `Description` 改为用途备注。
5. 最后验证非目标 Tag、Devices、PLC 映射和测量参数未改变。

如果无法确认 `.Text` 的当前业务语义、默认值来源或持久化时序，必须停止并列为 Kevin 确认项。

## 七、写入安全

- 原项目和原始文件只读，禁止删除或覆盖。
- 只修改明确的项目副本或已备份工作文件。
- VGAGE Pro 运行时不得外部编辑项目文件。
- 备份不得覆盖已有文件，名称应包含任务或日期。
- 保持原文件 UTF-8 BOM、CRLF 和属性顺序。
- 使用同目录临时文件、flush、`fsync` 和原子替换。
- 修改 `CodeModule.vgs` 时只写 Sub/Function body，不添加 Imports、Namespace 或 Module 包装。
- 不得因 Tag 迁移连带改变 PLC 地址、方向、Bit、`IO Enabled`、测量公式、名义值、公差或 RTG 时序。

## 八、测试与验收

至少建立以下专项契约：

1. 目标 Tag 集合与数量精确。
2. 每个目标的 XML 元素名、`Name` 完全一致，且 `Text` 有效值为 `Name`（显式 `Text=Name` 或缺失时按 `Name` 解释）。
3. 每个目标 `Description` 为预期非空中文用途备注。
4. `Description` 不等于默认值，且不保存枚举列表。
5. 目标 String Tag 的业务代码不存在 `TagName.Text` 读取。
6. 默认值存在于正确 Form/启动代码，且写入 `.Value`。
7. 有 `SaveSelection` 的控件只在空值时使用默认值。
8. 默认初始化不位于 `Refresh` 或周期事件。
9. PLC/HMI/Equation 驱动 Tag 不存在强制默认值写入。
10. 修改前后 `Devices` 子树完全一致。
11. 非目标 Tag 属性完全一致。
12. HMI `DestTag`、`SourceTag` 无悬空引用。
13. XML/config 全量解析通过。
14. BOM、CRLF、脚本块形态保持。
15. 迁移工具重复执行后文件 SHA 不变。
16. 项目既有专项回归通过。
17. `vgage-program-reviewer` 没有新增 FAIL Rule ID。

静态检查不能代替 Windows/VGAGE 编译、真实 PLC/MES、界面持久化和设备节拍验证。未完成现场验证时结论必须标记为 `DONE_WITH_CONCERNS`。

## 九、交付输出

必须报告：

- 目标 Tag 数量和四类分类；
- 每个字段的迁移规则；
- 默认值、所属界面/事件和保存优先级；
- 修改文件与精确差异；
- 明确排除和未修改项；
- 备份路径、修改前后哈希和回滚方法；
- 专项测试、XML/引用/格式/幂等结果；
- reviewer 基线对比；
- Windows/VGAGE 和现场确认清单。

## 十、禁止项

- 禁止 `Text = Name + 中文说明`。
- 禁止把业务值、默认值或枚举保存在 `Text` / `Description`。
- 禁止新代码读取 `Tag.Text` 作为业务值。
- 禁止无范围地批量修改历史 Tag。
- 禁止仅根据 `Type` 猜默认值或运行语义。
- 禁止为统一格式改动 `Name`、`Type`、Equation 或 PLC 映射。
- 禁止在未检查代码引用、持久化和初始化时序时宣布完成。

## 十一、三个 Worker 的发布方式

- 本 Skill 由 main 维护和发布，三个 Worker 只读取受控链接。
- 更新先作为 Skill Workshop 待审提案，不直接改 live Skill。
- Kevin/main 审核冲突、适用范围、证据和回滚后再 apply。
- apply 后三个 Worker 通过同一受控 Skill 版本获得规则。
- 旧版“说明型 Text=Name+中文说明”和“业务值型 Text 保持纯值”的规则视为废止，不再用于新建 Tag；历史项目只按第六章受控迁移。
