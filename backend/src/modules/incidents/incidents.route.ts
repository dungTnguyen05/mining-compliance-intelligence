import { Router } from "express";

import { getIncidentSummary } from "./incidents.repository.js";

export const incidentsRouter = Router();

// return incident totals grouped by type and severity
incidentsRouter.get("/summary", async (_request, response, next) => {
    try {
        const summary = await getIncidentSummary();

        response.status(200).json(summary);
    }
    catch (error) {
        // send errors to the Express error handler
        next(error);
    }
});
