---
name: "vgage-measurement-probe-binding-check"
description: "Check and fill Probe bindings after creating or changing VGAGE Measurements."
---

# VGAGE Measurement Probe Binding Check

Use this skill as a delivery checklist when creating, migrating, or modifying VGAGE Pro Measurement items.

## When to Use

- Creating VGAGE Pro Measurement items.
- Batch-generating or migrating Measurements in `VGA.xml`.
- Modifying a Measurement's `Equation`, `Text`, `Nominal`, tolerances, or Probe relationship.
- Verifying measurement items generated from DWG drawings or technical agreements before handoff.

## Core Rule

After creating or modifying every Measurement, check whether that Measurement has selected the Probe actually used by the inspection item.

If a Measurement formula references a Probe, for example:

```vb
Return p2n3.Value
```

Then the corresponding Measurement node must include a Probe binding, for example:

```xml
<Probes>
  <Id>27</Id>
</Probes>
```

The `27` must come from the `Id` of the top-level `Probe` whose `Name` is `p2n3` in `VGA.xml`.

## Default Check Steps

1. Read top-level `<Probes>` in `VGA.xml` and build a `Probe Name -> Id` lookup table.
2. Traverse `<Measurements>` under each Part.
3. For each inspection Measurement, check:
   - Whether `Equation` references a Probe's `.Value`.
   - Whether the Measurement has a `<Probes>` node.
   - Whether `<Probes><Id>` matches the Id of the Probe referenced by the formula.
4. If `<Probes />` is empty, look up the Probe Id from the referenced Probe Name and fill it.
5. If one Measurement formula involves multiple Probes or cannot be resolved unambiguously, do not auto-fill it; list it as an operator-confirmation item.
6. After modification, verify:
   - `VGA.xml` can still be parsed.
   - Empty `<Probes />` nodes have been rechecked.
   - Every inspection Measurement's referenced Probe matches `<Probes><Id>`.

## Risk Boundary

- This rule only handles the selection binding between Measurement and Probe.
- It does not automatically confirm sensor direction, sign, formula direction, tolerance source, or field measurement action.
- Probe direction, sign, `Nominal`, `USL/LSL`, and RTG timing remain operator or field-confirmation risks.
- Before modifying a real project, back up the original file or work on a copy.

## Handoff Checklist

Before handing off a VGAGE Pro project, the Measurement checklist must include:

- Whether the Probe referenced by each inspection formula exists.
- Whether the Measurement selected the corresponding Probe.
- Whether formula-referenced Probe and `<Probes><Id>` are consistent.
- Whether ambiguous Probe bindings are listed as operator-confirmation items.
