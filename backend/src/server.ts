import { createApp } from "./app.js";
import { environment } from "./config.js";

const app = createApp({
    allowedOrigins: environment.ALLOWED_ORIGINS
});

app.listen(environment.API_PORT, "0.0.0.0", () => {
    console.log(
        `API listening on http://0.0.0.0:${environment.API_PORT}`
    );
});
