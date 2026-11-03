import { BookOpenCheckIcon, FileCheck2Icon, QuoteIcon } from "lucide-react";
import { Outlet, useLocation } from "react-router";

import { Badge } from "@/components/ui/badge";
import { PublicControls } from "@/components/layout/public-controls";
import { useT } from "@/lib/i18n";
import { useDocumentTitle } from "@/lib/use-document-title";

const ICONS = [QuoteIcon, FileCheck2Icon, BookOpenCheckIcon];

function authTitle(pathname: string, t: ReturnType<typeof useT>): string {
  if (pathname.startsWith("/register")) {
    return t.auth.registerTitle;
  }
  if (pathname.startsWith("/verify")) {
    return t.auth.verifyTitle;
  }
  if (pathname.startsWith("/reset/confirm")) {
    return t.auth.resetConfirmTitle;
  }
  if (pathname.startsWith("/reset")) {
    return t.auth.resetTitle;
  }
  return t.auth.loginTitle;
}

export function AuthLayout() {
  const t = useT();
  const { pathname } = useLocation();
  useDocumentTitle(`${authTitle(pathname, t)} · ${t.app.name}`);

  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <PublicControls />
      <aside className="hidden flex-col justify-between border-r bg-muted/30 p-10 lg:flex">
        <div className="space-y-2">
          <Badge variant="secondary">{t.app.course}</Badge>
          <span className="block text-2xl font-semibold tracking-tight">
            {t.app.name}
          </span>
          <p className="max-w-sm text-sm text-muted-foreground">{t.app.tagline}</p>
        </div>
        <ul className="space-y-5">
          {t.auth.checks.map((check, index) => {
            const Icon = ICONS[index] ?? QuoteIcon;
            return (
              <li key={check.title} className="flex gap-3">
                <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <div className="space-y-1">
                  <p className="text-sm font-medium">{check.title}</p>
                  <p className="max-w-sm text-sm text-muted-foreground">
                    {check.body}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
        <p className="text-xs text-muted-foreground">{t.app.course} · HKUST</p>
      </aside>
      <main id="main" className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
