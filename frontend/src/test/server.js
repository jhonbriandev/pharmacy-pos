import { setupServer } from "msw/node";

/**
 * Servidor MSW compartido por las pruebas.
 *
 * Se inicia sin handlers: cada prueba declara solo los endpoints que usa. Asi
 * un cambio en el contrato de la API rompe la prueba concreta y no se esconde
 * detras de un mock global que siempre responde lo mismo.
 */
export const server = setupServer();
