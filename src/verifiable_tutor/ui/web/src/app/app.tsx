import { createBrowserRouter, RouterProvider } from "react-router";

import { Providers } from "@/app/providers";
import { routes } from "@/app/routes";
import { isPreviewRuntime } from "@/lib/preview/mode";

const router = createBrowserRouter(routes);

export function App() {
  return (
    <Providers preview={isPreviewRuntime()}>
      <RouterProvider router={router} />
    </Providers>
  );
}
