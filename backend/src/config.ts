import { config as loadEnvironment } from "dotenv";
import { fileURLToPath } from "node:url";
import { z } from "zod";

const environmentPath = fileURLToPath(
  new URL("../../.env", import.meta.url)
);

loadEnvironment({ path: environmentPath });

const environmentSchema = z.object({
  DB_HOST: z.string().min(1),
  DB_PORT: z.coerce.number().int().positive(),
  DB_NAME: z.string().min(1),
  DB_USER: z.string().min(1),
  DB_PASSWORD: z.string(),
  API_PORT: z.coerce.number().int().min(1).max(65535).default(3000)
});

export const environment = environmentSchema.parse(process.env);
