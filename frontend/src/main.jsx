import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { ensureCsrf } from "@/api/client";
import { AppProviders } from "@/app/providers";
import { router } from "@/app/router";
import "./index.css";

// El token CSRF debe existir antes del primer POST (login incluido).
void ensureCsrf();
const container = document.getElementById("root");
if (!container) {
  throw new Error("Falta el elemento #root en index.html.");
}
createRoot(container).render(
  <StrictMode>
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  </StrictMode>,
);
