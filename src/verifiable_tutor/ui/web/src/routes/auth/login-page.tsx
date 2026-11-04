import { useState } from "react";
import { Link, useSearchParams } from "react-router";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { authApi } from "@/lib/api/auth";
import { apiErrorMessage } from "@/lib/api/errors";
import { useSession } from "@/lib/auth/session";
import { useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";

export function LoginPage() {
  const t = useT();
  const { isPreview } = usePreview();
  const { refresh } = useSession();
  const [params] = useSearchParams();
  const [email, setEmail] = useState(() =>
    isPreview ? "" : (params.get("email") ?? ""),
  );
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(() => {
    if (isPreview) {
      return null;
    }
    if (params.get("verified") === "1") {
      return t.auth.emailVerifiedNotice;
    }
    if (params.get("reset") === "1") {
      return t.auth.passwordUpdatedNotice;
    }
    return null;
  });
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }
    if (password.length < 8) {
      setNotice(t.auth.shortPassword);
      return;
    }
    if (isPreview) {
      setNotice(t.common.previewNotice);
      return;
    }
    if (!email.includes("@")) {
      setNotice(t.auth.invalidEmail);
      return;
    }
    setPending(true);
    setNotice(null);
    try {
      await authApi.login(email.trim(), password);
      await refresh();
    } catch (error) {
      setNotice(apiErrorMessage(error, t));
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h1 className="text-lg font-semibold">{t.auth.loginTitle}</h1>
        </CardTitle>
        <CardDescription>{t.auth.loginSubtitle}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} noValidate>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="email">{t.auth.email}</FieldLabel>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder={t.auth.emailPlaceholder}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
              <FieldDescription>{t.auth.domainHint}</FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="password">{t.auth.password}</FieldLabel>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                placeholder={t.auth.passwordPlaceholder}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            {notice ? (
              <Alert>
                <AlertDescription>{notice}</AlertDescription>
              </Alert>
            ) : null}
            <Button type="submit" disabled={pending}>
              {pending ? t.auth.signingIn : t.auth.signIn}
            </Button>
          </FieldGroup>
        </form>
      </CardContent>
      <CardFooter className="flex flex-col items-start gap-2 text-sm">
        <p className="text-muted-foreground">
          {t.auth.noAccount}{" "}
          <Link to="/register" className="underline underline-offset-4">
            {t.auth.createAccount}
          </Link>
        </p>
        <Link to="/reset" className="text-muted-foreground underline underline-offset-4">
          {t.auth.forgotPassword}
        </Link>
      </CardFooter>
    </Card>
  );
}
