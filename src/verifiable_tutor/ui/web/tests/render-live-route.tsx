import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";

import { Providers } from "@/app/providers";
import { routes } from "@/app/routes";
import type { SessionValue } from "@/lib/auth/session";

/**
 * Render a route in live mode. Tests stub `fetch` first (usually with
 * `createFetchStub`) and pass `session` only when they want a fixed session.
 */
export function renderLiveRoute(
  path: string,
  {
    session,
    lang = "en",
  }: {
    session?: SessionValue;
    lang?: "en" | "zh";
  } = {},
) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });

  render(
    <Providers preview={false} session={session} initialLang={lang}>
      <RouterProvider router={router} />
    </Providers>,
  );

  return router;
}
