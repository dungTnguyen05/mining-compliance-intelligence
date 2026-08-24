import { Router } from "express";

import {
    getIncidentAiFindings,
    getIncidentAiSummary,
    getIncidentSummary,
    getIncidentTrends
} from "./incidents.repository.js";

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

// return monthly incident totals grouped by type and severity
incidentsRouter.get("/trends", async (_request, response, next) => {
    try {
        const trends = await getIncidentTrends();

        response.status(200).json({
            data: trends
        });
    }
    catch (error) {
        // send errors to the Express error handler
        next(error);
    }
});

// return grounded AI findings with source incident context
incidentsRouter.get("/ai-findings", async (_request, response, next) => {
    try {
        const findings = await getIncidentAiFindings();

        response.status(200).json({
            data: findings
        });
    }
    catch (error) {
        next(error);
    }
});

// summarize psychosocial and severity-review findings
incidentsRouter.get("/ai-summary", async (_request, response, next) => {
    try {
        const summary = await getIncidentAiSummary();

        response.status(200).json(summary);
    }
    catch (error) {
        next(error);
    }
});
