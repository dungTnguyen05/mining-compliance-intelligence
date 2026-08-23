import { Router } from "express";

import { getMonthlyEmissions } from "./emissions.repository.js";

export const emissionsRouter = Router();

// return monthly Scope 1 and Scope 2 emissions
emissionsRouter.get("/monthly", async (_request, response, next) => {
    try {
        const emissions = await getMonthlyEmissions();

        response.status(200).json({
            unit: "kgCO2e",
            data: emissions
        });
    }
    catch (error) {
        // send errors to the Express error handler
        next(error);
    }
});
