import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

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

export function ResetConfirmPage() {
  const t = useT();
  const navigate = useNavigate();
  const { isPreview } = usePreview();
  const [params] = useSearchParams();
  const token = (params.get("token") ?? "").trim();
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
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
    if (password !== confirmation) {
      setNotice(t.auth.passwordsDiffer);
      return;
    }
    if (isPreview) {
      setNotice(t.common.previewNotice);
      return;
    }
    setPending(true);
    setNotice(null);
    try {
      await authApi.reset(token, password);
      navigate("/login?reset=1");
    } catch (error) {
      setNotice(apiErrorMessage(error, t));
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h1 className="text-lg font-semibold">{t.auth.resetConfirmTitle}</h1>
        </CardTitle>
        <CardDescription>{t.auth.resetConfirmSubtitle}</CardDescription>
      </CardHeader>
      <CardContent>
        {token ? (
          <form onSubmit={submit} noValidate>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="new-password">
                  {t.auth.newPassword}
                </FieldLabel>
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
              <Button type="submit" disabled={pending}>
                {pending ? t.auth.updatingPassword : t.auth.updatePassword}
              </Button>
            </FieldGroup>
          </form>
        ) : (
          <Alert>
            <AlertDescription>{t.auth.invalidResetToken}</AlertDescription>
          </Alert>
        )}
      </CardContent>
      <CardFooter className="text-sm">
        {token ? (
          <Link
            to="/login"
            className="text-muted-foreground underline underline-offset-4"
          >
            {t.auth.backToSignIn}
          </Link>
        ) : (
          <Link
            to="/reset"
            className="text-muted-foreground underline underline-offset-4"
          >
            {t.auth.requestReset}
          </Link>
        )}
      </CardFooter>
    </Card>
  );
}
