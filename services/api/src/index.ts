import dotenv from "dotenv";
import { buildApp } from "./app.js";

dotenv.config({ path: new URL("../.env", import.meta.url) });

const app = await buildApp();

await app.listen({ port: app.ctx.env.PORT, host: "0.0.0.0" });

