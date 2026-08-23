import { Router } from "express";

import { getMonthlyEmissions } from "./emissions.repository.js";

export const emissionsRouter = Router();

emissionsRouter.get("/monthly", async (_request, response, next) => {
    try {
        const emissions = await getMonthlyEmissions();

        response.status(200).json({
            unit: "kgCO2e",
            data: emissions
        });
    }

    catch (error) {
        next(error);
    }
});
