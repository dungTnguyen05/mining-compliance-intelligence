import request from "supertest";
import { describe, expect, it, vi } from "vitest";

vi.mock(
    "../src/modules/data-quality/data-quality.repository.js",
    () => ({
        getDataQualityReport: vi.fn().mockResolvedValue({
            summary: {
                totalIssues: 2,
                byAction: {
                    fixed: 1,
                    flagged: 1,
                    rejected: 0
                },
                byDataset: {
                    fuel_deliveries: 1,
                    suppliers: 1
                }
            },
            issues: [
                {
                    id: 1,
                    dataset: "fuel_deliveries",
                    issueType: "negative fuel quantity and cost",
                    action: "fixed",
                    recordKey: "INV-41777",
                    details: {
                        rows_fixed: 1
                    },
                    createdAt: "2026-08-24T00:00:00.000Z"
                },
                {
                    id: 2,
                    dataset: "suppliers",
                    issueType: "invalid abn",
                    action: "flagged",
                    recordKey: "63004085616",
                    details: {
                        supplier_name: "Ironline Fuel Distributors Pty Ltd"
                    },
                    createdAt: "2026-08-24T00:00:00.000Z"
                }
            ]
        })
    })
);

import { createApp } from "../src/app.js";

describe("GET /api/data-quality", () => {
    it("returns a structured data quality report", async () => {
        const response = await request(createApp())
            .get("/api/data-quality");

        expect(response.status).toBe(200);
        expect(response.body.summary).toEqual({
            totalIssues: 2,
            byAction: {
                fixed: 1,
                flagged: 1,
                rejected: 0
            },
            byDataset: {
                fuel_deliveries: 1,
                suppliers: 1
            }
        });

        expect(response.body.issues).toHaveLength(2);
        expect(response.body.issues[0]).toMatchObject({
            dataset: "fuel_deliveries",
            issueType: "negative fuel quantity and cost",
            action: "fixed",
            recordKey: "INV-41777"
        });
    });
});
