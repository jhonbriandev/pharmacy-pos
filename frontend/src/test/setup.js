import "@testing-library/jest-dom/vitest";

import { cleanup, configure } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";

import { server } from "./server";

// Las pruebas del POS esperan a un debounce de 250 ms antes de que llegue la
// respuesta. Con cuatro archivos corriendo en paralelo, un segundo de espera
// por defecto es demasiado justo y produce fallos intermitentes.
configure({ asyncUtilTimeout: 4000 });

beforeAll(() => {
  // MSW 3 renombro la opcion: un frame sin handler es un fallo de la prueba.
  server.listen({
    onUnhandledFrame: "error",
  });
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
