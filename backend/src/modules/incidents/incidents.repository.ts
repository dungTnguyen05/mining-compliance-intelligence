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
