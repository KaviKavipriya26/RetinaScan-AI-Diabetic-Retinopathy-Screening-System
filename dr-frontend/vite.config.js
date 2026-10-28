import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Port 5173 is already allowed in backend CORS
export default defineConfig({ plugins: [react()], server: { port: 5173 } });
