import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";

import { server } from "./server";

beforeAll(() => {
  // MSW 3 renombro la opcion: un frame sin handler es un fallo de la prueba.
  server.listen({ onUnhandledFrame: "error" });
});

beforeEach(() => {
  // El cliente HTTP lee el token CSRF de la cookie; en jsdom no hay backend
  // que la establezca, asi que se simula la respuesta de /auth/csrf/.
  document.cookie = "csrftoken=test-token; path=/";
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
