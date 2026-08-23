import { Router } from "express";

import { getDataQualityReport } from "./data-quality.repository.js";

export const dataQualityRouter = Router();

// return fixed, flagged and rejected data quality issues
dataQualityRouter.get("/", async (_request, response, next) => {
    try {
        const report = await getDataQualityReport();

        response.status(200).json(report);
    }
    catch (error) {
        // send errors to the Express error handler
        next(error);
    }
});
