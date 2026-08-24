import request from "supertest";
import { describe, expect, it, vi } from "vitest";

vi.mock(
    "../src/modules/emissions/emissions.repository.js",
    () => ({
        getMonthlyEmissions: vi.fn().mockResolvedValue([
            {
                month: "2025-01",
                scope1KgCO2e: 100,
                scope2KgCO2e: 50,
                totalKgCO2e: 150,
                missingScopes: []
            }
        ])
    })
);

import { createApp } from "../src/app.js";

describe("GET /api/emissions/monthly", () => {
    it("returns monthly emissions by scope", async () => {
        const response = await request(createApp())
            .get("/api/emissions/monthly");

        expect(response.status).toBe(200);
        expect(response.body).toEqual({
            unit: "kgCO2e",
            data: [
                {
                    month: "2025-01",
                    scope1KgCO2e: 100,
                    scope2KgCO2e: 50,
                    totalKgCO2e: 150,
                    missingScopes: []
                }
            ]
        });
    });
});
