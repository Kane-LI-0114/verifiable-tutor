import { useState } from "react";
import { Link } from "react-router";

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
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { authApi } from "@/lib/api/auth";
import { apiErrorMessage } from "@/lib/api/errors";
import { useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";

export function ResetPage() {
  const t = useT();
  const { isPreview } = usePreview();
  const [email, setEmail] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }
    if (!email.includes("@")) {
      setNotice(t.auth.invalidEmail);
      return;
    }
    if (isPreview) {
      setNotice(t.auth.sent);
      return;
    }
    setPending(true);
    setNotice(null);
    try {
      const response = await authApi.requestReset(email.trim());
      setNotice(
        response.email_delivery === "log"
          ? `${t.auth.sent} ${t.auth.checkLog}`
          : t.auth.sent,
      );
    } catch (error) {
      setNotice(apiErrorMessage(error, t));
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h1 className="text-lg font-semibold">{t.auth.resetTitle}</h1>
        </CardTitle>
        <CardDescription>{t.auth.resetSubtitle}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} noValidate>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="reset-email">{t.auth.email}</FieldLabel>
              <Input
                id="reset-email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder={t.auth.emailPlaceholder}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Field>
            {notice ? (
              <Alert>
                <AlertDescription>{notice}</AlertDescription>
              </Alert>
            ) : null}
            <Button type="submit" disabled={pending}>
              {pending ? t.auth.sendingLink : t.auth.requestReset}
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
