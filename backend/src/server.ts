import { createApp } from "./app.js";
import { environment } from "./config.js";

const app = createApp();

app.listen(environment.API_PORT, () => {
  console.log(
    `API listening on http://localhost:${environment.API_PORT}`
  );
});
