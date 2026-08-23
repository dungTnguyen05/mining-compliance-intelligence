from ai_taxonomy import HAZARD_DOMAINS, EVENT_MECHANISMS

# allowed psychosocial hazard types
PSYCHOSOCIAL_TYPES = (
    "job_demands",
    "low_job_control",
    "poor_support",
    "lack_of_role_clarity",
    "poor_change_management",
    "inadequate_reward_and_recognition",
    "poor_organizational_justice",
    "traumatic_events_or_material",
    "remote_or_isolated_work",
    "poor_physical_environment",
    "violence_or_aggression",
    "bullying",
    "harassment",
    "conflict_or_poor_workplace_relationships",
    "work_related_fatigue",
)

# allowed severity review results
SEVERITY_CONSISTENCY = (
    "consistent",
    "appears_inconsistent",
    "insufficient_context",
)

SUGGESTED_SEVERITIES = (
    "Low",
    "Medium",
    "High",
    "Not assessed",
)

# fields the model must return for each incident
INCIDENT_FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "primary_hazard_domain": {
            "type": "string",
            "enum": HAZARD_DOMAINS,
        },
        "secondary_hazard_domains": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": HAZARD_DOMAINS,
            },
        },
        "event_mechanism": {
            "type": "string",
            "enum": EVENT_MECHANISMS,
        },
        "psychosocial_hazard": {
            "type": "boolean",
        },
        "psychosocial_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": PSYCHOSOCIAL_TYPES,
            },
        },
        "severity_consistency": {
            "type": "string",
            "enum": SEVERITY_CONSISTENCY,
        },
        "suggested_severity": {
            "type": "string",
            "enum": SUGGESTED_SEVERITIES,
        },
        "category_evidence_quote": {
            "type": "string",
        },
        "severity_evidence_quote": {
            "type": ["string", "null"],
        },
        "explanation": {
            "type": "string",
        },
    },
    "required": [
        "primary_hazard_domain",
        "secondary_hazard_domains",
        "event_mechanism",
        "psychosocial_hazard",
        "psychosocial_types",
        "severity_consistency",
        "suggested_severity",
        "category_evidence_quote",
        "severity_evidence_quote",
        "explanation",
    ],
    "additionalProperties": False,
}

# response format passed to the OpenAI client
INCIDENT_FINDING_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "incident_finding",
        "strict": True,
        "schema": INCIDENT_FINDING_SCHEMA,
    },
}
