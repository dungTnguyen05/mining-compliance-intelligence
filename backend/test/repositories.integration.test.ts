import { afterAll, describe, expect, it } from "vitest";

import { database } from "../src/db.js";
import { getDataQualityReport } from "../src/modules/data-quality/data-quality.repository.js";
import { getMonthlyEmissions } from "../src/modules/emissions/emissions.repository.js";
import { getIncidentTrends } from "../src/modules/incidents/incidents.repository.js";

afterAll(async () => {
    await database.end();
});

describe("backend calculations and summaries", () => {
    it("calculates monthly emissions with the correct scopes", async () => {
        const emissions = await getMonthlyEmissions();

        expect(emissions).toHaveLength(18);

        expect(emissions.find((item) => item.month === "2025-01"))
            .toEqual({
                month: "2025-01",
                scope1KgCO2e: 1079589.03,
                scope2KgCO2e: 1457844.07,
                totalKgCO2e: 2537433.1
            });

        // keep months that contain only one emissions scope
        expect(emissions.find((item) => item.month === "2025-11"))
            .toEqual({
                month: "2025-11",
                scope1KgCO2e: 0,
                scope2KgCO2e: 1445513.57,
                totalKgCO2e: 1445513.57
            });

        for (const month of emissions) {
            expect(month.totalKgCO2e).toBeCloseTo(
                month.scope1KgCO2e + month.scope2KgCO2e,
                2
            );
        }
    });

    it("combines incident type and severity counts by month", async () => {
        const trends = await getIncidentTrends();

        expect(trends.length).toBeGreaterThan(0);

        for (const month of trends) {
            const typeTotal = month.byType.reduce(
                (total, item) => total + item.count,
                0
            );

            const severityTotal = month.bySeverity.reduce(
                (total, item) => total + item.count,
                0
            );

            expect(typeTotal).toBe(month.totalIncidents);
            expect(severityTotal).toBe(month.totalIncidents);
        }
    });

    it("summarizes every structured data quality issue", async () => {
        const report = await getDataQualityReport();

        expect(report.summary).toEqual({
            totalIssues: 21,
            byAction: {
                fixed: 5,
                flagged: 16,
                rejected: 0
            },
            byDataset: {
                incident_register: 1,
                suppliers: 15,
                electricity_meter_readings: 1,
                fuel_deliveries: 4
            }
        });

        expect(report.issues).toHaveLength(21);

        for (const issue of report.issues) {
            expect(issue.details).toEqual(expect.any(Object));
            expect(issue.issueType.length).toBeGreaterThan(0);
        }
    });
});
