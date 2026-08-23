import { database } from "../../db.js";

export type DataQualityAction = "fixed" | "flagged" | "rejected";

// PostgreSQL returns BIGSERIAL values as strings
interface DataQualityIssueRow {
    id: string;
    dataset: string;
    issue_type: string;
    action: DataQualityAction;
    record_key: string | null;
    details: Record<string, unknown>;
    created_at: Date;
}

export interface DataQualityIssue {
    id: number;
    dataset: string;
    issueType: string;
    action: DataQualityAction;
    recordKey: string | null;
    details: Record<string, unknown>;
    createdAt: string;
}

export interface DataQualitySummary {
    totalIssues: number;
    byAction: Record<DataQualityAction, number>;
    byDataset: Record<string, number>;
}

export interface DataQualityReport {
    summary: DataQualitySummary;
    issues: DataQualityIssue[];
}

// return unresolved issues first, followed by rejected and fixed issues
const dataQualityIssuesQuery = `
    SELECT
        id,
        dataset,
        issue_type,
        action,
        record_key,
        details,
        created_at
    FROM data_quality_issues
    ORDER BY
        CASE action
            WHEN 'flagged' THEN 1
            WHEN 'rejected' THEN 2
            ELSE 3
        END,
        dataset,
        id
`;

export async function getDataQualityReport(): Promise<DataQualityReport> {
    const result =
        await database.query<DataQualityIssueRow>(
            dataQualityIssuesQuery
        );

    const byAction: Record<DataQualityAction, number> = {
        fixed: 0,
        flagged: 0,
        rejected: 0
    };

    const byDataset: Record<string, number> = {};

    // format issues and build summary counts from the same records
    const issues = result.rows.map((row) => {
        byAction[row.action] += 1;
        byDataset[row.dataset] = (byDataset[row.dataset] ?? 0) + 1;

        return {
            id: Number(row.id),
            dataset: row.dataset,
            issueType: row.issue_type,
            action: row.action,
            recordKey: row.record_key,
            details: row.details,
            createdAt: row.created_at.toISOString()
        };
    });

    return {
        summary: {
            totalIssues: issues.length,
            byAction,
            byDataset
        },
        issues
    };
}
