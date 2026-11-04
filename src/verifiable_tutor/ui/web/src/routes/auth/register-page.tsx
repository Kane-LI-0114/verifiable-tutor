import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";

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
import { useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";

/** Offline demo fixture: the domains a preview build accepts, no backend call. */
const PREVIEW_EMAIL_DOMAINS = ["connect.ust.hk", "ust.hk"];

/** The backend owns the allowed domains; this only checks the address shape. */
const EMAIL_ADDRESS = /^[^\s@]+@[^\s@]+$/;

function isAllowedEmail(value: string, domains: string[] | null): boolean {
  const address = value.trim();
  if (!EMAIL_ADDRESS.test(address)) {
    return false;
  }
  if (domains === null) {
    // The configuration is still loading or could not be loaded, so let the
    // backend decide instead of falling back to a hardcoded domain list.
    return true;
  }
  const domain = address.slice(address.lastIndexOf("@") + 1).toLowerCase();
  return domains.some((allowed) => allowed.toLowerCase() === domain);
}

export function RegisterPage() {
  const t = useT();
  const navigate = useNavigate();
  const { isPreview } = usePreview();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [domains, setDomains] = useState<string[] | null>(() =>
    isPreview ? PREVIEW_EMAIL_DOMAINS : null,
  );

  useEffect(() => {
    if (isPreview) {
      return;
    }
    let active = true;
    authApi
      .domains()
      .then((response) => {
        if (active) {
          setDomains(response.domains);
        }
      })
      .catch(() => {
        // Keep the null list: the backend still validates the domain.
      });
    return () => {
      active = false;
    };
  }, [isPreview]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }
    if (!isAllowedEmail(email, domains)) {
      setNotice(t.auth.invalidEmail);
      return;
    }
    if (password.length < 8) {
      setNotice(t.auth.shortPassword);
      return;
    }
    if (isPreview) {
      setNotice(t.auth.checkLog);
      return;
    }
    setPending(true);
    setNotice(null);
    try {
      const response = await authApi.register(email.trim(), password);
      navigate(`/verify?email=${encodeURIComponent(response.email)}`);
    } catch (error) {
      setNotice(apiErrorMessage(error, t));
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h1 className="text-lg font-semibold">{t.auth.registerTitle}</h1>
        </CardTitle>
        <CardDescription>{t.auth.registerSubtitle}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} noValidate>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="register-email">{t.auth.email}</FieldLabel>
              <Input
                id="register-email"
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
              <FieldLabel htmlFor="register-password">{t.auth.password}</FieldLabel>
              <Input
                id="register-password"
                name="password"
                type="password"
                autoComplete="new-password"
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
              {pending ? t.auth.creatingAccount : t.auth.register}
            </Button>
          </FieldGroup>
        </form>
      </CardContent>
      <CardFooter className="text-sm">
        <Link to="/login" className="text-muted-foreground underline underline-offset-4">
          {t.auth.backToSignIn}
        </Link>
      </CardFooter>
    </Card>
  );
}
