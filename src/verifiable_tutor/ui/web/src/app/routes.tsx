import { Navigate, type RouteObject } from "react-router";

import { AppShell } from "@/components/layout/app-shell";
import { AuthLayout } from "@/components/layout/auth-layout";
import { PublicOnly, RequireAuth, RequireInstructor } from "@/app/guards";
import { LoginPage } from "@/routes/auth/login-page";
import { RegisterPage } from "@/routes/auth/register-page";
import { ResetConfirmPage } from "@/routes/auth/reset-confirm-page";
import { ResetPage } from "@/routes/auth/reset-page";
import { VerifyPage } from "@/routes/auth/verify-page";
import { ChatPage } from "@/routes/chat/chat-page";
import { BuildsPage } from "@/routes/instructor/builds-page";
import { DeadlinesPage } from "@/routes/instructor/deadlines-page";
import { DocumentPage } from "@/routes/knowledge/document-page";
import { KnowledgePage } from "@/routes/knowledge/knowledge-page";
import { NotFoundPage } from "@/routes/not-found-page";
import { PracticePage } from "@/routes/practice/practice-page";

export const routes: RouteObject[] = [
  {
    element: <PublicOnly />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          { path: "/login", element: <LoginPage /> },
          { path: "/register", element: <RegisterPage /> },
          { path: "/verify", element: <VerifyPage /> },
          { path: "/reset", element: <ResetPage /> },
          { path: "/reset/confirm", element: <ResetConfirmPage /> },
        ],
      },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="/chat" replace /> },
          { path: "chat", element: <ChatPage /> },
          { path: "chat/:sessionId", element: <ChatPage /> },
          { path: "practice", element: <PracticePage /> },
          { path: "knowledge", element: <KnowledgePage /> },
          { path: "knowledge/docs/:docId", element: <DocumentPage /> },
          {
            element: <RequireInstructor />,
            children: [
              { path: "instructor/builds", element: <BuildsPage /> },
              { path: "instructor/deadlines", element: <DeadlinesPage /> },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
];
