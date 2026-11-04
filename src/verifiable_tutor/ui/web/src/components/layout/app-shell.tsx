import {
  BookOpenIcon,
  CalendarClockIcon,
  HammerIcon,
  LogOutIcon,
  MessageSquareIcon,
  PlusIcon,
  ShieldCheckIcon,
  UserIcon,
  WaypointsIcon,
} from "lucide-react";
import { useEffect, useRef, type ComponentType } from "react";
import { NavLink, Outlet, useLocation, useParams } from "react-router";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { useSession } from "@/lib/auth/session";
import { useConversations } from "@/lib/session/conversations";
import { useT } from "@/lib/i18n";
import { useDocumentTitle } from "@/lib/use-document-title";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { PreviewControls } from "@/components/layout/preview-controls";

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  end?: boolean;
}

// The sidebar component stores its state in a cookie. A single-page shell has no
// server to read it back, so restore the last choice before the first paint.
function readSidebarCookie(): boolean {
  if (typeof document === "undefined") {
    return true;
  }
  const match = document.cookie.match(/(?:^|;\s*)sidebar_state=(true|false)/);
  return match ? match[1] === "true" : true;
}

function currentTitle(pathname: string, t: ReturnType<typeof useT>): string {
  if (pathname.startsWith("/chat")) {
    return t.chat.title;
  }
  if (pathname.startsWith("/practice")) {
    return t.practice.title;
  }
  if (pathname.startsWith("/knowledge")) {
    return t.knowledge.title;
  }
  if (pathname.startsWith("/instructor/builds")) {
    return t.builds.title;
  }
  if (pathname.startsWith("/instructor/deadlines")) {
    return t.deadlines.title;
  }
  return t.app.name;
}

function SidebarNavItem({ item }: { item: NavItem }) {
  const { pathname } = useLocation();
  const active = item.end
    ? pathname === item.to
    : pathname === item.to || pathname.startsWith(`${item.to}/`);

  return (
    <SidebarMenuItem>
      <SidebarMenuButton asChild isActive={active} tooltip={item.label}>
        <NavLink to={item.to}>
          <item.icon />
          <span>{item.label}</span>
        </NavLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}

function SidebarAccountMenu({ showDetails }: { showDetails: boolean }) {
  const t = useT();
  const { user, signOut } = useSession();
  const roleLabel =
    user?.role === "instructor" ? t.common.instructor : t.common.student;

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              aria-label={user?.email ?? t.nav.account}
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <Avatar className="size-8 shrink-0">
                <AvatarFallback>
                  <UserIcon className="size-4" />
                </AvatarFallback>
              </Avatar>
              {showDetails ? (
                <span className="flex min-w-0 flex-col text-left">
                  <span className="truncate text-sm">
                    {user?.email ?? t.nav.account}
                  </span>
                  <span className="truncate text-xs text-muted-foreground">
                    {roleLabel}
                  </span>
                </span>
              ) : null}
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="top" align="start" className="w-56">
            <DropdownMenuLabel className="flex items-center justify-between gap-2">
              <span className="truncate">{user?.email ?? t.nav.account}</span>
              <Badge variant="secondary">{roleLabel}</Badge>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={() => {
                void signOut();
              }}
            >
              <LogOutIcon />
              {t.common.signOut}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}

function AppSidebar() {
  const t = useT();
  const { user } = useSession();
  const { sessionId } = useParams();
  const { pathname } = useLocation();
  const { state, setOpenMobile } = useSidebar();
  const {
    sessions,
    status: conversationsStatus,
    refresh: refreshConversations,
    prefetchHistory,
  } = useConversations();
  const expanded = state === "expanded";

  // On a phone the navigation lives in a sheet; a destination tap has to close
  // it or the reviewer lands on a page they cannot see.
  useEffect(() => {
    setOpenMobile(false);
  }, [pathname, setOpenMobile]);

  const primary: NavItem[] = [
    { to: "/practice", label: t.nav.practice, icon: WaypointsIcon },
    { to: "/knowledge", label: t.nav.knowledge, icon: BookOpenIcon },
  ];

  const instructor: NavItem[] =
    user?.role === "instructor"
      ? [
          { to: "/instructor/builds", label: t.nav.builds, icon: HammerIcon, end: true },
          {
            to: "/instructor/deadlines",
            label: t.nav.deadlines,
            icon: CalendarClockIcon,
            end: true,
          },
        ]
      : [];

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild size="lg" tooltip={t.app.name}>
              <NavLink to="/chat" aria-label={t.app.name}>
                <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <ShieldCheckIcon className="size-4" />
                </span>
                {expanded ? (
                  <span className="flex min-w-0 flex-col text-left">
                    <span className="truncate text-sm font-semibold">
                      {t.app.name}
                    </span>
                    <span className="truncate text-xs text-muted-foreground">
                      {t.app.course}
                    </span>
                  </span>
                ) : null}
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={pathname === "/chat"}
                  tooltip={t.nav.newChat}
                >
                  <NavLink to="/chat">
                    <PlusIcon />
                    <span>{t.nav.newChat}</span>
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
              {primary.map((item) => (
                <SidebarNavItem key={item.to} item={item} />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {instructor.length > 0 ? (
          <SidebarGroup>
            <SidebarGroupLabel>{t.nav.instructor}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {instructor.map((item) => (
                  <SidebarNavItem key={item.to} item={item} />
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        <SidebarGroup>
          <SidebarGroupLabel>{t.nav.conversations}</SidebarGroupLabel>
          <SidebarGroupContent>
            {conversationsStatus === "loading" ? (
              <div className="space-y-1 px-2 py-1" aria-busy="true">
                <Skeleton className="h-7 w-full" />
                <Skeleton className="h-7 w-4/5" />
                <Skeleton className="h-7 w-3/5" />
              </div>
            ) : conversationsStatus === "error" ? (
              <div className="space-y-2 px-2 py-1">
                <p className="text-xs text-muted-foreground">
                  {t.chat.sessionsLoadError}
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    void refreshConversations();
                  }}
                >
                  {t.common.retry}
                </Button>
              </div>
            ) : sessions.length === 0 ? (
              <p className="px-2 text-xs text-muted-foreground">
                {t.nav.noConversations}
              </p>
            ) : (
              <SidebarMenu aria-label={t.a11y.conversations}>
                {sessions.map((session) => (
                  <SidebarMenuItem key={session.id}>
                    <SidebarMenuButton
                      asChild
                      isActive={sessionId === session.id}
                      tooltip={session.title ?? session.id}
                    >
                      <NavLink
                        to={`/chat/${session.id}`}
                        onPointerEnter={() => prefetchHistory(session.id)}
                        onFocus={() => prefetchHistory(session.id)}
                      >
                        <MessageSquareIcon />
                        <span>{session.title ?? session.id}</span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            )}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarAccountMenu showDetails={expanded} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

function TopBar() {
  const t = useT();
  const { pathname } = useLocation();
  const title = currentTitle(pathname, t);
  useDocumentTitle(`${title} · ${t.app.name}`);

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b px-3">
      <SidebarTrigger aria-label={t.common.openNavigation} />
      <span className="flex h-4 shrink-0 items-center">
        <Separator orientation="vertical" className="h-4" />
      </span>
      <span className="truncate text-sm font-medium">{title}</span>
      <div className="ml-auto flex items-center gap-1">
        <PreviewControls />
        <LanguageToggle />
      </div>
    </header>
  );
}

export function AppShell() {
  const t = useT();
  const { pathname } = useLocation();
  const firstRender = useRef(true);

  // A client-side navigation does not move focus by itself. Put it on the new
  // main region so keyboard and screen-reader users start at the new content.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    document.getElementById("main")?.focus({ preventScroll: true });
  }, [pathname]);

  return (
    <SidebarProvider className="h-svh min-h-0" defaultOpen={readSidebarCookie()}>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm focus:shadow"
      >
        {t.common.skipToContent}
      </a>
      <AppSidebar />
      <SidebarInset id="main" tabIndex={-1} className="min-h-0 min-w-0 focus:outline-none">
        <TopBar />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
