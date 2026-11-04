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
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";
import { authApi } from "@/lib/api/auth";
import { apiErrorMessage } from "@/lib/api/errors";
import { useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";

export function VerifyPage() {
  const t = useT();
  const navigate = useNavigate();
  const { isPreview } = usePreview();
  const [params] = useSearchParams();
  const email = params.get("email") ?? "";
  const [code, setCode] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }
    if (code.length !== 6) {
      setNotice(t.auth.sixDigits);
      return;
    }
    if (isPreview) {
      setNotice(t.common.previewNotice);
      return;
    }
    if (email === "") {
      setNotice(t.auth.invalidEmail);
      return;
    }
    setPending(true);
    setNotice(null);
    try {
      await authApi.verify(email, code);
      navigate(`/login?email=${encodeURIComponent(email)}&verified=1`);
    } catch (error) {
      setNotice(apiErrorMessage(error, t));
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h1 className="text-lg font-semibold">{t.auth.verifyTitle}</h1>
        </CardTitle>
        <CardDescription>{t.auth.verifySubtitle}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} noValidate>
          <FieldGroup>
            {email ? (
              <p className="text-sm text-muted-foreground">{email}</p>
            ) : null}
            <Field>
              <FieldLabel htmlFor="code">{t.auth.code}</FieldLabel>
              <InputOTP
                id="code"
                maxLength={6}
                value={code}
                onChange={setCode}
                aria-label={t.auth.code}
              >
                <InputOTPGroup>
                  <InputOTPSlot index={0} />
                  <InputOTPSlot index={1} />
                  <InputOTPSlot index={2} />
                  <InputOTPSlot index={3} />
                  <InputOTPSlot index={4} />
                  <InputOTPSlot index={5} />
                </InputOTPGroup>
              </InputOTP>
              <FieldDescription>{t.auth.checkLog}</FieldDescription>
            </Field>
            {notice ? (
              <Alert>
                <AlertDescription>{notice}</AlertDescription>
              </Alert>
            ) : null}
            <Button type="submit" disabled={pending}>
              {pending ? t.auth.verifying : t.auth.verify}
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled
              title={t.common.unavailable}
            >
              {t.auth.resend}
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
