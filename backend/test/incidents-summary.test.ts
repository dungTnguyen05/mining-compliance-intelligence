import request from "supertest";
import { describe, expect, it, vi } from "vitest";

vi.mock(
    "../src/modules/incidents/incidents.repository.js",
    () => ({
        getIncidentSummary: vi.fn().mockResolvedValue({
            totalIncidents: 6,
            byType: [
                {
                    typeCode: "VEH",
                    count: 3
                },
                {
                    typeCode: "ENV",
                    count: 3
                }
            ],
            bySeverity: [
                {
                    severity: "Low",
                    count: 1
                },
                {
                    severity: "Medium",
                    count: 2
                },
                {
                    severity: "High",
                    count: 3
                }
            ]
        }),
        getIncidentTrends: vi.fn(),
        getIncidentAiFindings: vi.fn(),
        getIncidentAiSummary: vi.fn()
    })
);

import { createApp } from "../src/app.js";

describe("GET /api/incidents/summary", () => {
    it("returns incident totals by type and severity", async () => {
        const response = await request(createApp())
            .get("/api/incidents/summary");

        expect(response.status).toBe(200);
        expect(response.body).toEqual({
            totalIncidents: 6,
            byType: [
                {
                    typeCode: "VEH",
                    count: 3
                },
                {
                    typeCode: "ENV",
                    count: 3
                }
            ],
            bySeverity: [
                {
                    severity: "Low",
                    count: 1
                },
                {
                    severity: "Medium",
                    count: 2
                },
                {
                    severity: "High",
                    count: 3
                }
            ]
        });
    });
});
