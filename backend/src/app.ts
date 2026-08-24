import express from "express";

import { emissionsRouter } from "./modules/emissions/emissions.route.js";
import { incidentsRouter } from "./modules/incidents/incidents.route.js";
import { dataQualityRouter } from "./modules/data-quality/data-quality.route.js";

interface AppOptions {
    allowedOrigins?: string[];
}

export function createApp(options: AppOptions = {}) {
    const app = express();
    const allowedOrigins = new Set(options.allowedOrigins ?? []);

    // remove the default Express response header
    app.disable("x-powered-by");

    // allow browser requests only from configured frontend origins
    app.use((request, response, next) => {
        const origin = request.headers.origin;

        if (!origin || !allowedOrigins.has(origin)) {
            next();
            return;
        }

        response.setHeader("Access-Control-Allow-Origin", origin);
        response.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
        response.setHeader(
            "Access-Control-Allow-Headers",
            "Accept, Content-Type"
        );
        response.setHeader("Vary", "Origin");

        if (request.method === "OPTIONS") {
            response.sendStatus(204);
            return;
        }

        next();
    });

    // read JSON request bodies
    app.use(express.json());

    // report whether the API is running
    app.get("/health", (_request, response) => {
        response.status(200).json({
            status: "ok"
        });
    });

    // register monthly emissions routes
    app.use("/api/emissions", emissionsRouter);

    // register incident routes
    app.use("/api/incidents", incidentsRouter);

    // register data quality routes
    app.use("/api/data-quality", dataQualityRouter);

    return app;
}
