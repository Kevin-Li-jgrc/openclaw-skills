from __future__ import annotations

from typing import Any, Callable

from rules_binding import (
    check_binding_ambiguity,
    check_bound_probe_ids_exist,
    check_measurement_probe_binding,
    check_measurement_probe_exists,
    check_probe_name_id_unique,
)
from rules_dependencies import (
    check_computed_probe_dependencies,
    check_direct_probe_dependencies,
    check_measurement_dependencies,
    check_no_extra_probe_dependencies,
    check_probe_dependency_cycles,
    check_probe_equation_objects,
    check_summary_measurement_rtg0,
)
from rules_structure import (
    check_form_references,
    check_measurement_runtime_fields,
    check_probe_runtime_fields,
    check_project_parse,
    check_project_structure,
)
from rules_data import (
    check_auto_archive_path,
    check_external_write_resilience,
    check_marking_anti_duplicate,
    check_part_text,
    check_required_vga_fields,
)
from rules_io import (
    check_imbus_probe_equations,
    check_imbus_probe_mapping,
    check_imbus_text_and_channels,
    check_io_comment_tag_symmetry,
    check_orbit_probe_names,
    check_tag_semantics,
)
from rules_measurement import (
    check_dimensional_digits,
    check_dynamic_data_cycles,
    check_evaluate_when_selected,
    check_feature_names,
    check_feature_global_names,
    check_feature_types,
    check_masterset_text,
    check_measurement_operation,
    check_measurement_return_zero,
    check_probe_return_zero,
    check_string_datetime_not_empty,
)
from rules_code import (
    check_bestfit_hardcoded_recalc,
    check_calibration_due_reset,
    check_code_module_format,
    check_offect_api,
    check_periodic_code_risks,
)
from rules_review_semantics import (
    check_angle_encoder_consistency,
    check_diameter_nominal_semantics,
    check_feature_geometry_setup,
    check_form_object_mappings,
    check_formula_surface,
    check_master_certpoint,
    check_master_nominal_actual,
    check_measurement_name_symbol,
    check_nominal_literal,
    check_probe_symbol_semantics,
    check_probe_symbol_convention,
    check_temperature_masterset,
    check_temperature_traceability,
)


RuleFunction = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]

RULES: dict[str, RuleFunction] = {
    "VG-PRJ-001": check_project_structure,
    "VG-STR-001": check_project_parse,
    "VG-BIND-001": check_probe_name_id_unique,
    "VG-BIND-002": check_measurement_probe_exists,
    "VG-BIND-003": check_bound_probe_ids_exist,
    "VG-BIND-004": check_measurement_probe_binding,
    "VG-BIND-006": check_binding_ambiguity,
    "VG-DEP-001": check_probe_equation_objects,
    "VG-DEP-002": check_direct_probe_dependencies,
    "VG-DEP-003": check_computed_probe_dependencies,
    "VG-DEP-004": check_no_extra_probe_dependencies,
    "VG-DEP-005": check_probe_dependency_cycles,
    "VG-DEP-006": check_measurement_dependencies,
    "VG-DEP-007": check_summary_measurement_rtg0,
}

CONTEXT_RULES = {
    "VG-STR-002": check_required_vga_fields,
    "VG-STR-004": check_measurement_runtime_fields,
    "VG-STR-005": check_probe_runtime_fields,
    "VG-STR-012": check_form_references,
    "VG-STR-013": check_code_module_format,
    "VG-STR-011": check_form_object_mappings,
    "VG-STR-014": check_formula_surface,
    "VG-STR-016": check_part_text,
    "VG-IO-010": check_io_comment_tag_symmetry,
    "VG-IO-002": check_imbus_probe_mapping,
    "VG-IO-003": check_imbus_probe_equations,
    "VG-IO-011": check_imbus_text_and_channels,
    "VG-IO-012": check_orbit_probe_names,
    "VG-IO-013": check_tag_semantics,
    "VG-MEAS-011": check_dynamic_data_cycles,
    "VG-MEAS-001": check_nominal_literal,
    "VG-MEAS-002": check_diameter_nominal_semantics,
    "VG-MEAS-003": check_probe_symbol_convention,
    "VG-MEAS-005": check_feature_types,
    "VG-MEAS-006": check_offect_api,
    "VG-MEAS-007": check_bestfit_hardcoded_recalc,
    "VG-MEAS-008": check_feature_global_names,
    "VG-MEAS-010": check_feature_geometry_setup,
    "VG-MEAS-012": check_dimensional_digits,
    "VG-MEAS-013": check_probe_return_zero,
    "VG-MEAS-014": check_probe_symbol_semantics,
    "VG-MEAS-015": check_angle_encoder_consistency,
    "VG-MEAS-016": check_masterset_text,
    "VG-MEAS-017": check_temperature_masterset,
    "VG-MEAS-018": check_master_certpoint,
    "VG-MEAS-019": check_master_nominal_actual,
    "VG-MEAS-020": check_feature_names,
    "VG-MEAS-021": check_measurement_return_zero,
    "VG-MEAS-022": check_evaluate_when_selected,
    "VG-MEAS-023": check_measurement_name_symbol,
    "VG-MEAS-024": check_measurement_operation,
    "VG-MEAS-025": check_string_datetime_not_empty,
    "VG-DATA-012": check_auto_archive_path,
    "VG-DATA-005": check_external_write_resilience,
    "VG-DATA-007": check_marking_anti_duplicate,
    "VG-DATA-011": check_temperature_traceability,
    "VG-SAFE-011": check_periodic_code_risks,
    "VG-SAFE-013": check_calibration_due_reset,
}


def run_deterministic_rules(
    facts: dict[str, Any], catalog: dict[str, Any], context: dict[str, Any]
) -> list[dict[str, Any]]:
    by_id = {rule["rule_id"]: rule for rule in catalog["rules"]}
    results = [RULES[rule_id](facts, by_id[rule_id]) for rule_id in RULES]
    results.extend(
        CONTEXT_RULES[rule_id](facts, by_id[rule_id], context)
        for rule_id in CONTEXT_RULES
    )
    return results
