import { LanguagesIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useI18n, useT } from "@/lib/i18n";

export function LanguageToggle() {
  const t = useT();
  const { lang, toggleLang } = useI18n();

  return (
    <Button
      type="button"
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
  );
}
