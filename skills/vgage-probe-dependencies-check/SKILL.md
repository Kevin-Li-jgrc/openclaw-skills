---
name: "vgage-probe-dependencies-check"
description: "Check and fill Dependencies after creating or changing VGAGE computed Probes."
---

# VGAGE Probe Dependencies Check

Use this skill as a delivery checklist when creating, migrating, or modifying VGAGE Pro top-level Probes.

## When to Use

- Creating VGAGE Pro top-level Probes.
- Batch-generating or migrating `<Probes>` in `VGA.xml`.
- Modifying a Probe's `Equation`.
- Verifying sensors and computed Probes generated from DWG drawings or technical agreements before handoff.

## Core Rule

For every Probe under top-level `<Probes>` in `VGA.xml`:

- If the current Probe returns directly from a sensor/channel object, for example `Return DP1.Value`, keep `<Dependencies />` empty. No Probe dependency should be selected.
- If the current Probe returns values from other Probes, for example `Return p2.Value + p3.Value`, the current Probe's `<Dependencies>` must include the Ids of all referenced Probes.

Example:

```xml
<p2n3 Id="27" Name="p2n3" Equation="... Return p2.Value + p3.Value ...">
  <Dependencies>
    <Id>2</Id>
    <Id>3</Id>
  </Dependencies>
</p2n3>
```

## Default Check Steps

1. Read top-level `<Probes>` in `VGA.xml` and build a `Probe Name -> Id` lookup table.
2. Traverse each Probe's `Equation`.
3. Identify `xxx.Value` references in formulas:
   - If `xxx` is a DP, IO, Tag, or other non-Probe object, do not treat it as a Probe dependency.
   - If `xxx` is a Probe Name that exists in top-level `<Probes>`, add that Probe to the current Probe's Dependencies.
4. For direct-channel Probes, keep `<Dependencies />` empty.
5. For computed Probes, ensure `<Dependencies><Id>` matches the Probe Ids referenced in the formula, de-duplicated in formula order.
6. If a formula is too complex to determine dependencies safely, do not guess; list it as an operator-confirmation item.

## Verification Requirements

After modification, verify at minimum:

- `VGA.xml` can still be parsed.
- Every computed Probe's formula-referenced Probes match `<Dependencies><Id>`.
- Direct-channel Probes should not have non-empty Dependencies.
- Only Dependencies were changed; Probe formulas, channels, direction, nominal values, tolerances, and Measurement bindings were not changed.

## Risk Boundary

- This rule only handles Probe dependency selection.
- It does not confirm sensor direction, sign, formula direction, channel assignment, or field measurement action.
- Formula direction, sign, and DP channel meaning remain operator or field-confirmation risks.
- Before modifying a real project, back up the original file or work on a copy.

## Handoff Checklist

Before handing off a VGAGE Pro project, the Probe checklist must include:

- Whether direct-channel Probe Dependencies remain empty.
- Whether objects referenced by computed Probe formulas exist in top-level Probes.
- Whether each computed Probe's `<Dependencies><Id>` matches the formula-referenced Probes.
- Whether ambiguous dependencies are listed as operator-confirmation items.
