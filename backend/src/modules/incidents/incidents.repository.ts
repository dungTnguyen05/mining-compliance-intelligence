import { database } from "../../db.js";

// PostgreSQL returns COUNT(*) as a string because it uses the BIGINT type
interface CountRow {
    count: string;
}

interface TypeCountRow extends CountRow {
    type_code: string;
}

interface SeverityCountRow extends CountRow {
    severity: string;
}

interface IncidentTrendRow extends CountRow {
    month: string;
    type_code: string;
    severity: string;
}

export interface IncidentTypeCount {
    typeCode: string;
    count: number;
}

export interface IncidentSeverityCount {
    severity: string;
    count: number;
}

export interface IncidentSummary {
    totalIncidents: number;
    byType: IncidentTypeCount[];
    bySeverity: IncidentSeverityCount[];
}

export interface IncidentTrend {
    month: string;
    totalIncidents: number;
    byType: IncidentTypeCount[];
    bySeverity: IncidentSeverityCount[];
}

// count all cleaned incidents
const totalIncidentsQuery = `
    SELECT COUNT(*) AS count
    FROM incidents
`;

// count incidents by type, highest count first
const incidentsByTypeQuery = `
    SELECT
        type_code,
        COUNT(*) AS count
    FROM incidents
    GROUP BY type_code
    ORDER BY count DESC, type_code
`;

// count incidents by severity in Low, Medium, High order
const incidentsBySeverityQuery = `
    SELECT
        severity,
        COUNT(*) AS count
    FROM incidents
    GROUP BY severity
    ORDER BY
        CASE severity
            WHEN 'Low' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'High' THEN 3
            ELSE 4
        END
`;

// count incidents by month, type and severity
const incidentTrendsQuery = `
    SELECT
        TO_CHAR(
            DATE_TRUNC('month', incident_date),
            'YYYY-MM'
        ) AS month,
        type_code,
        severity,
        COUNT(*) AS count
    FROM incidents
    GROUP BY
        DATE_TRUNC('month', incident_date),
        type_code,
        severity
    ORDER BY
        DATE_TRUNC('month', incident_date),
        type_code,
        CASE severity
            WHEN 'Low' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'High' THEN 3
            ELSE 4
        END
`;

export async function getIncidentSummary(): Promise<IncidentSummary> {
    // run independent queries at the same time (concurrently)
    const [
        totalResult,
        typeResult,
        severityResult
    ] = await Promise.all([
        database.query<CountRow>(totalIncidentsQuery),
        database.query<TypeCountRow>(incidentsByTypeQuery),
        database.query<SeverityCountRow>(incidentsBySeverityQuery)
    ]);

    // convert database count strings to numbers for the API response
    return {
        totalIncidents: Number(totalResult.rows[0]?.count ?? 0),

        byType: typeResult.rows.map((row) => ({
            typeCode: row.type_code,
            count: Number(row.count)
        })),

        bySeverity: severityResult.rows.map((row) => ({
            severity: row.severity,
            count: Number(row.count)
        }))
    };
}

export async function getIncidentTrends(): Promise<IncidentTrend[]> {
    const result =
        await database.query<IncidentTrendRow>(
            incidentTrendsQuery
        );

    const trends = new Map<string, IncidentTrend>();

    // combine type and severity counts into one record for each month
    for (const row of result.rows) {
        const count = Number(row.count);

        let month = trends.get(row.month);

        if (!month) {
            month = {
                month: row.month,
                totalIncidents: 0,
                byType: [],
                bySeverity: []
            };

            trends.set(row.month, month);
        }

        month.totalIncidents += count;

        const type = month.byType.find(
            (item) => item.typeCode === row.type_code
        );

        if (type) {
            type.count += count;
        }
        else {
            month.byType.push({
                typeCode: row.type_code,
                count
            });
        }

        const severity = month.bySeverity.find(
            (item) => item.severity === row.severity
        );

        if (severity) {
            severity.count += count;
        }
        else {
            month.bySeverity.push({
                severity: row.severity,
                count
            });
        }
    }

    const severityOrder: Record<string, number> = {
        Low: 1,
        Medium: 2,
        High: 3
    };

    // keep type and severity results in a consistent order
    return Array.from(trends.values()).map((month) => ({
        ...month,

        byType: month.byType.sort(
            (first, second) =>
                second.count - first.count
                || first.typeCode.localeCompare(second.typeCode)
        ),

        bySeverity: month.bySeverity.sort(
            (first, second) =>
                (severityOrder[first.severity] ?? 4)
                - (severityOrder[second.severity] ?? 4)
        )
    }));
}

interface IncidentAiFindingRow {
    incident_id: string;
    incident_date: string;
    location: string;
    type_code: string;
    recorded_severity: string;
    description: string;
    source_row: number;
    source_record_hash: string;
    primary_hazard_domain: string;
    secondary_hazard_domains: string[];
    event_mechanism: string;
    psychosocial_hazard: boolean;
    psychosocial_types: string[];
    severity_consistency: string;
    suggested_severity: string;
    category_evidence_quote: string;
    severity_evidence_quote: string | null;
    explanation: string;
    response_id: string | null;
    model: string;
    processed_at: Date;
    attempts: number;
}

interface IncidentAiSummaryRow {
    total_analyzed: string;
    psychosocial_hazards: string;
    severity_inconsistencies: string;
    insufficient_context: string;
}

export interface IncidentAiFinding {
    incidentId: string;
    incidentDate: string;
    location: string;
    recordedTypeCode: string;
    recordedSeverity: string;
    description: string;
    sourceRow: number;
    recordHash: string;
    primaryHazardDomain: string;
    secondaryHazardDomains: string[];
    eventMechanism: string;
    psychosocialHazard: boolean;
    psychosocialTypes: string[];
    severityConsistency: string;
    suggestedSeverity: string;
    categoryEvidenceQuote: string;
    severityEvidenceQuote: string | null;
    explanation: string;
    responseId: string | null;
    model: string;
    processedAt: string;
    attempts: number;
}

export interface IncidentAiSummary {
    totalAnalyzed: number;
    psychosocialHazards: number;
    severityInconsistencies: number;
    insufficientContext: number;
}

const incidentAiFindingsQuery = `
    SELECT
        incidents.incident_id,
        TO_CHAR(
            incidents.incident_date,
            'YYYY-MM-DD'
        ) AS incident_date,
        incidents.location,
        incidents.type_code,
        incidents.severity AS recorded_severity,
        incidents.description,
        incidents.source_row,
        findings.source_record_hash,
        findings.primary_hazard_domain,
        findings.secondary_hazard_domains,
        findings.event_mechanism,
        findings.psychosocial_hazard,
        findings.psychosocial_types,
        findings.severity_consistency,
        findings.suggested_severity,
        findings.category_evidence_quote,
        findings.severity_evidence_quote,
        findings.explanation,
        findings.response_id,
        findings.model,
        findings.processed_at,
        findings.attempts
    FROM incident_ai_findings AS findings
    INNER JOIN incidents
        ON incidents.source_record_hash = findings.source_record_hash
    ORDER BY
        incidents.incident_date,
        incidents.source_row
`;

const incidentAiSummaryQuery = `
    SELECT
        COUNT(*) AS total_analyzed,
        COUNT(*) FILTER (
            WHERE psychosocial_hazard
        ) AS psychosocial_hazards,
        COUNT(*) FILTER (
            WHERE severity_consistency = 'appears_inconsistent'
        ) AS severity_inconsistencies,
        COUNT(*) FILTER (
            WHERE severity_consistency = 'insufficient_context'
        ) AS insufficient_context
    FROM incident_ai_findings
`;

export async function getIncidentAiFindings(): Promise<IncidentAiFinding[]> {
    const result = await database.query<IncidentAiFindingRow>(
        incidentAiFindingsQuery
    );

    return result.rows.map((row) => ({
        incidentId: row.incident_id,
        incidentDate: row.incident_date,
        location: row.location,
        recordedTypeCode: row.type_code,
        recordedSeverity: row.recorded_severity,
        description: row.description,
        sourceRow: row.source_row,
        recordHash: row.source_record_hash,
        primaryHazardDomain: row.primary_hazard_domain,
        secondaryHazardDomains: row.secondary_hazard_domains,
        eventMechanism: row.event_mechanism,
        psychosocialHazard: row.psychosocial_hazard,
        psychosocialTypes: row.psychosocial_types,
        severityConsistency: row.severity_consistency,
        suggestedSeverity: row.suggested_severity,
        categoryEvidenceQuote: row.category_evidence_quote,
        severityEvidenceQuote: row.severity_evidence_quote,
        explanation: row.explanation,
        responseId: row.response_id,
        model: row.model,
        processedAt: row.processed_at.toISOString(),
        attempts: row.attempts
    }));
}

export async function getIncidentAiSummary(): Promise<IncidentAiSummary> {
    const result = await database.query<IncidentAiSummaryRow>(
        incidentAiSummaryQuery
    );
    const summary = result.rows[0];

    return {
        totalAnalyzed: Number(summary?.total_analyzed ?? 0),
        psychosocialHazards: Number(summary?.psychosocial_hazards ?? 0),
        severityInconsistencies: Number(
            summary?.severity_inconsistencies ?? 0
        ),
        insufficientContext: Number(summary?.insufficient_context ?? 0)
    };
}
