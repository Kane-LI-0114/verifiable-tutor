import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";

import { Providers } from "@/app/providers";
import { routes } from "@/app/routes";
import type { PreviewRole } from "@/lib/preview/session";
import type { PreviewState } from "@/lib/types";

export function renderRoute(
  path: string,
  {
    role = "student",
    pageState = "normal",
    lang = "en",
  }: {
    role?: PreviewRole;
    pageState?: PreviewState;
    lang?: "en" | "zh";
  } = {},
) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });

  render(
    <Providers
      previewRole={role}
      previewState={pageState}
      initialLang={lang}
    >
      <RouterProvider router={router} />
    </Providers>,
  );

  return router;
}
