import pg from "pg";

import { environment } from "./config.js";

const { Pool } = pg;

export const database = new Pool({
  host: environment.DB_HOST,
  port: environment.DB_PORT,
  database: environment.DB_NAME,
  user: environment.DB_USER,
  password: environment.DB_PASSWORD,
  max: 10,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000
});

database.on("error", (error) => {
  console.error("Unexpected PostgreSQL connection error:", error);
});
