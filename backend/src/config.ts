import { config as loadEnvironment } from "dotenv";
import { fileURLToPath } from "node:url";
import { z } from "zod";

const environmentPath = fileURLToPath(
    new URL("../../.env", import.meta.url)
);

loadEnvironment({ path: environmentPath });

const portSchema = z.coerce.number().int().min(1).max(65535);

const environmentSchema = z.object({
    DB_HOST: z.string().min(1),
    DB_PORT: z.coerce.number().int().positive(),
    DB_NAME: z.string().min(1),
    DB_USER: z.string().min(1),
    DB_PASSWORD: z.string(),
    API_PORT: portSchema.optional(),
    PORT: portSchema.optional(),
    ALLOWED_ORIGINS: z.string().default("")
}).transform((values) => ({
    ...values,
    API_PORT: values.PORT ?? values.API_PORT ?? 3000,
    ALLOWED_ORIGINS: values.ALLOWED_ORIGINS
        .split(",")
        .map((origin) => origin.trim())
        .filter(Boolean)
}));

export const environment = environmentSchema.parse(process.env);
