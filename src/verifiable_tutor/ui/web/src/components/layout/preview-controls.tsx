import { FlaskConicalIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";
import type { PreviewRole } from "@/lib/preview/session";
import type { PreviewState } from "@/lib/types";

const ROLES: PreviewRole[] = ["student", "instructor", "signed-out"];
const STATES: PreviewState[] = ["normal", "loading", "empty", "error"];

function roleLabel(t: ReturnType<typeof useT>, role: PreviewRole): string {
  if (role === "instructor") {
    return t.preview.instructor;
  }
  if (role === "signed-out") {
    return t.preview.signedOut;
  }
  return t.preview.student;
}

export function PreviewControls() {
  const t = useT();
  const { isPreview, role, pageState, setRole, setPageState } = usePreview();

  if (!isPreview) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" aria-label={t.preview.label}>
          <FlaskConicalIcon />
          <Badge variant="outline">{t.preview.badge}</Badge>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuLabel>{t.preview.role}</DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={role}
          onValueChange={(value) => setRole(value as PreviewRole)}
        >
          {ROLES.map((item) => (
            <DropdownMenuRadioItem key={item} value={item}>
              {roleLabel(t, item)}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator />
        <DropdownMenuLabel>{t.preview.state}</DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={pageState}
          onValueChange={(value) => setPageState(value as PreviewState)}
        >
          {STATES.map((item) => (
            <DropdownMenuRadioItem key={item} value={item}>
              {t.preview[item]}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
