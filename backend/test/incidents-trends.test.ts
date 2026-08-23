import request from "supertest";
import { describe, expect, it, vi } from "vitest";

vi.mock(
    "../src/modules/incidents/incidents.repository.js",
    () => ({
        getIncidentSummary: vi.fn(),

        getIncidentTrends: vi.fn().mockResolvedValue([
            {
                month: "2025-01",
                totalIncidents: 4,
                byType: [
                    {
                        typeCode: "VEH",
                        count: 3
                    },
                    {
                        typeCode: "ENV",
                        count: 1
                    }
                ],
                bySeverity: [
                    {
                        severity: "Low",
                        count: 2
                    },
                    {
                        severity: "Medium",
                        count: 1
                    },
                    {
                        severity: "High",
                        count: 1
                    }
                ]
            }
        ])
    })
);

import { createApp } from "../src/app.js";

describe("GET /api/incidents/trends", () => {
    it("returns monthly incident trends", async () => {
        const response = await request(createApp())
            .get("/api/incidents/trends");

        expect(response.status).toBe(200);
        expect(response.body).toEqual({
            data: [
                {
                    month: "2025-01",
                    totalIncidents: 4,
                    byType: [
                        {
                            typeCode: "VEH",
                            count: 3
                        },
                        {
                            typeCode: "ENV",
                            count: 1
                        }
                    ],
                    bySeverity: [
                        {
                            severity: "Low",
                            count: 2
                        },
                        {
                            severity: "Medium",
                            count: 1
                        },
                        {
                            severity: "High",
                            count: 1
                        }
                    ]
                }
            ]
        });
    });
});
