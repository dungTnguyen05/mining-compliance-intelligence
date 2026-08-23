import express from "express";

import { emissionsRouter } from "./modules/emissions/emissions.route.js";

export function createApp() {
    const app = express();

    app.disable("x-powered-by");
    app.use(express.json());

    app.get("/health", (_request, response) => {
        response.status(200).json({
            status: "ok"
        });
    });

    app.use("/api/emissions", emissionsRouter);

    return app;
}
