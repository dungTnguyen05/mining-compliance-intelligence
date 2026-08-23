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
