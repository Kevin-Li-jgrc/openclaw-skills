# 12279 VGAGE 保存往返证据（只读复核）

- 项目副本：`12279-L3-A2T-DRAFT_072326120733-scanner-mes-copy_20260723`。
- 保存时点：2026-07-24 09:44:08 +08:00。
- 保存后的 `IO.xml` SHA-256：`6c6fd38436292477a8b5fe1c8e9e8bc56118086bdda823df6fbfb82bff773bd8`。
- 自动 ZIP：`Backup/12279-L3-A2T-DRAFT_072426094408.zip`。
- ZIP 内 `IO.xml` SHA-256：`6c6fd38436292477a8b5fe1c8e9e8bc56118086bdda823df6fbfb82bff773bd8`，与当前文件相同。
- 74 个受控目标 Tag：显式 `Text=Name` 属性为 0 个、缺失 `Text` 为 74 个；每个 `Name` 和中文 `Description` 保留。

## RED 复现（支持证据，非正式成功测试）

- 命令：`VGAGE_12279_TARGET='/Volumes/工作资料备份/OneDrive/生产资料/项目/正在进行/12279-未完成/自动测量机例程/调试程序/12279-L3-A2T-DRAFT_072326120733-scanner-mes-copy_20260723' python3 -m unittest -v tests.test_12279_tag_text_defaults`（执行的是 r3 修订前的严格 `Text=Name` 断言）。
- 结果：exit `1`；9 个测试中的 74 个目标 Tag 子断言均为 `None != Name`。
- 原因：保存后的 VGAGE XML 省略了等于 `Name` 的显式 `Text` 属性，旧断言错误地将属性存在性当成字段有效值。
- GREEN 结果及其余成功回归保存在 `evidence.json/tests`；其正式 test 条目均为 exit `0`。

结论：VGAGE 保存把 `Text=Name` 规范化为属性省略。此证据仅证明 XML 保存往返语义；不替代 Windows/VGAGE 编译或现场 PLC/MES/界面验证。
