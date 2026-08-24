import request from "supertest";
import { describe, expect, it, vi } from "vitest";

vi.mock(
    "../src/modules/incidents/incidents.repository.js",
    () => ({
        getIncidentSummary: vi.fn(),
        getIncidentTrends: vi.fn(),

        getIncidentAiFindings: vi.fn().mockResolvedValue([
            {
                incidentId: "INC-2025-127",
                recordHash: "a".repeat(64),
                psychosocialHazard: true,
                psychosocialTypes: ["bullying"],
                severityConsistency: "consistent"
            }
        ]),

        getIncidentAiSummary: vi.fn().mockResolvedValue({
            totalAnalyzed: 5,
            psychosocialHazards: 1,
            severityInconsistencies: 1,
            insufficientContext: 2
        })
    })
);

import { createApp } from "../src/app.js";

describe("AI incident routes", () => {
    it("returns grounded findings with source identity", async () => {
        const response = await request(createApp())
            .get("/api/incidents/ai-findings");

        expect(response.status).toBe(200);
        expect(response.body.data).toEqual([
            expect.objectContaining({
                incidentId: "INC-2025-127",
                recordHash: "a".repeat(64),
                psychosocialHazard: true,
                psychosocialTypes: ["bullying"]
            })
        ]);
    });

    it("returns the AI incident summary", async () => {
        const response = await request(createApp())
            .get("/api/incidents/ai-summary");

        expect(response.status).toBe(200);
        expect(response.body).toEqual({
            totalAnalyzed: 5,
            psychosocialHazards: 1,
            severityInconsistencies: 1,
            insufficientContext: 2
        });
    });
});
