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
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n";

export function ResetConfirmPage() {
  const t = useT();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password.length < 8) {
      setNotice(t.auth.shortPassword);
      return;
    }
    if (password !== confirmation) {
      setNotice(t.auth.passwordsDiffer);
      return;
    }
    setNotice(t.common.previewNotice);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h1 className="text-lg font-semibold">{t.auth.resetConfirmTitle}</h1>
        </CardTitle>
        <CardDescription>{t.auth.resetSubtitle}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} noValidate>
          <FieldGroup>
            {token ? (
              <p className="text-xs text-muted-foreground">
                {token.slice(0, 8)}…
              </p>
            ) : null}
            <Field>
              <FieldLabel htmlFor="new-password">{t.auth.newPassword}</FieldLabel>
              <Input
                id="new-password"
                name="new-password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="confirm-password">
                {t.auth.confirmPassword}
              </FieldLabel>
              <Input
                id="confirm-password"
                name="confirm-password"
                type="password"
                autoComplete="new-password"
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
              />
            </Field>
            {notice ? (
              <Alert>
                <AlertDescription>{notice}</AlertDescription>
              </Alert>
            ) : null}
            <Button type="submit">{t.auth.updatePassword}</Button>
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
