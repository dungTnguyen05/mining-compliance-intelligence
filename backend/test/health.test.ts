import request from "supertest";
import { describe, expect, it } from "vitest";

import { createApp } from "../src/app.js";

describe("GET /health", () => {
    it("returns the API status", async () => {
        const response = await request(createApp()).get("/health");

        expect(response.status).toBe(200);
        expect(response.body).toEqual({
            status: "ok"
        });
    });

    it("allows a configured frontend origin", async () => {
        const app = createApp({
            allowedOrigins: ["https://ironbark.example"]
        });
        const response = await request(app)
            .get("/health")
            .set("Origin", "https://ironbark.example");

        expect(response.headers["access-control-allow-origin"]).toBe(
            "https://ironbark.example"
        );
    });

    it("does not allow an unconfigured frontend origin", async () => {
        const app = createApp({
            allowedOrigins: ["https://ironbark.example"]
        });
        const response = await request(app)
            .get("/health")
            .set("Origin", "https://untrusted.example");

        expect(response.headers["access-control-allow-origin"]).toBeUndefined();
    });
});
