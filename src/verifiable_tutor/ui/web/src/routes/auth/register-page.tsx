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
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n";

export function RegisterPage() {
  const t = useT();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.includes("@")) {
      setNotice(t.auth.invalidEmail);
      return;
    }
    if (password.length < 8) {
      setNotice(t.auth.shortPassword);
      return;
    }
    setNotice(t.auth.checkLog);
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
            <Button type="submit">{t.auth.register}</Button>
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
