# VGAGE Core Rules Snapshot

- Measurement 公式引用的 Probe 必须存在，且 `<Probes><Id>` 与实际读取对象一致。
- 直接通道 Probe 的 Dependencies 为空；计算 Probe 必须完整、无多余地列出引用 Probe。
- Measurement 读取其他 Measurement 时必须列出 Dependencies；纯汇总结果通常使用 RTG0。
- IO.xml 是 IMBus 通道到物理 Probe 的权威来源，不按名称猜通道。
- 对射和气动直径通常不减 `Me.Nominal`；其他场景按实际值/偏差语义确认。
- Feature/BestFit、Location、Direction、Offset、Correlation 和 Recalc 遵循已确认对象模型。
- CodeModule 外部文件使用 UTF-8 BOM、CRLF 和纯 Sub/Function 主体。
- 周期事件、PLC/IO、MES、打标、RTG 和全局事件属于高风险审查面。
