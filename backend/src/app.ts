import express from "express";

import { emissionsRouter } from "./modules/emissions/emissions.route.js";
import { incidentsRouter } from "./modules/incidents/incidents.route.js";

export function createApp() {
    const app = express();

    // remove the default Express response header
    app.disable("x-powered-by");

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

    return app;
}
