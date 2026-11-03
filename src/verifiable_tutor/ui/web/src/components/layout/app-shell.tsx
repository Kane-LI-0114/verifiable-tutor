import {
  BookOpenIcon,
  CalendarClockIcon,
  HammerIcon,
  LanguagesIcon,
  LogOutIcon,
  MessageSquareIcon,
  PlusIcon,
  ShieldCheckIcon,
  UserIcon,
  WaypointsIcon,
} from "lucide-react";
import type { ComponentType } from "react";
import { NavLink, Outlet, useLocation, useParams } from "react-router";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
} from "@/components/ui/sidebar";
import { useSession } from "@/lib/auth/session";
import { useI18n, useT } from "@/lib/i18n";
import { PREVIEW_SESSIONS } from "@/lib/preview/fixtures";
import { PreviewControls } from "@/components/layout/preview-controls";

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  end?: boolean;
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

function AppSidebar() {
  const t = useT();
  const { user } = useSession();
  const { sessionId } = useParams();

  const primary: NavItem[] = [
    { to: "/chat", label: t.nav.chat, icon: MessageSquareIcon },
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
              <NavLink to="/chat">
                <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <ShieldCheckIcon className="size-4" />
                </span>
                <span className="flex min-w-0 flex-col text-left">
                  <span className="truncate text-sm font-semibold">{t.app.name}</span>
                  <span className="truncate text-xs text-muted-foreground">
                    {t.app.course}
                  </span>
                </span>
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
                <SidebarMenuButton asChild tooltip={t.nav.newChat}>
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
            {PREVIEW_SESSIONS.length === 0 ? (
              <p className="px-2 text-xs text-muted-foreground">
                {t.nav.noConversations}
              </p>
            ) : (
              <SidebarMenu aria-label={t.a11y.conversations}>
                {PREVIEW_SESSIONS.map((session) => (
                  <SidebarMenuItem key={session.id}>
                    <SidebarMenuButton
                      asChild
                      isActive={sessionId === session.id}
                      tooltip={session.title ?? session.id}
                    >
                      <NavLink to={`/chat/${session.id}`}>
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
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild size="lg" tooltip={user?.email ?? t.nav.account}>
              <NavLink to="/chat">
                <Avatar className="size-8">
                  <AvatarFallback>
                    <UserIcon className="size-4" />
                  </AvatarFallback>
                </Avatar>
                <span className="flex min-w-0 flex-col text-left">
                  <span className="truncate text-sm">{user?.email ?? t.nav.account}</span>
                  <span className="truncate text-xs text-muted-foreground">
                    {user?.role === "instructor"
                      ? t.common.instructor
                      : t.common.student}
                  </span>
                </span>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

function TopBar() {
  const t = useT();
  const { pathname } = useLocation();
  const { user, signOut } = useSession();
  const { lang, toggleLang } = useI18n();

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b px-3">
      <SidebarTrigger aria-label={t.common.openNavigation} />
      <Separator orientation="vertical" className="h-4" />
      <span className="truncate text-sm font-medium">{currentTitle(pathname, t)}</span>
      <div className="ml-auto flex items-center gap-1">
        <PreviewControls />
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleLang}
          aria-label={t.common.language}
        >
          <LanguagesIcon />
          <span className="hidden sm:inline">
            {lang === "en" ? "中文" : "English"}
          </span>
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" aria-label={user?.email ?? t.nav.account}>
              <Avatar className="size-6">
                <AvatarFallback>
                  <UserIcon className="size-3.5" />
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="flex items-center justify-between gap-2">
              <span className="truncate">{user?.email ?? t.nav.account}</span>
              <Badge variant="secondary">
                {user?.role === "instructor"
                  ? t.common.instructor
                  : t.common.student}
              </Badge>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => signOut()}>
              <LogOutIcon />
              {t.common.signOut}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

export function AppShell() {
  const t = useT();

  return (
    <SidebarProvider className="h-svh min-h-0">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm focus:shadow"
      >
        {t.common.skipToContent}
      </a>
      <AppSidebar />
      <SidebarInset id="main" className="min-h-0">
        <TopBar />
        <div className="flex min-h-0 flex-1 flex-col">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
