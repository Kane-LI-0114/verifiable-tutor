import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { en, type Messages } from "./en";
import { zh } from "./zh";

export type Language = "en" | "zh";

const RESOURCES: Record<Language, Messages> = { en, zh };
const STORAGE_KEY = "vt.ui.language";

interface I18nValue {
  lang: Language;
  t: Messages;
  setLang: (lang: Language) => void;
  toggleLang: () => void;
}

const I18nContext = createContext<I18nValue | null>(null);

function readStoredLanguage(): string | null {
  try {
    return window.localStorage?.getItem(STORAGE_KEY) ?? null;
  } catch {
    // Private browsing and some test environments deny storage access.
    return null;
  }
}

function storeLanguage(lang: Language): void {
  try {
    window.localStorage?.setItem(STORAGE_KEY, lang);
  } catch {
    // The in-memory choice still applies for this session.
  }
}

function storedLanguage(): Language {
  if (typeof window === "undefined") {
    return "en";
  }
  return readStoredLanguage() === "zh" ? "zh" : "en";
}

export function I18nProvider({
  initialLang,
  children,
}: {
  initialLang?: Language;
  children: ReactNode;
}) {
  const [lang, setLangState] = useState<Language>(initialLang ?? storedLanguage);

  useEffect(() => {
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    storeLanguage(lang);
  }, [lang]);

  const setLang = useCallback((next: Language) => setLangState(next), []);
  const toggleLang = useCallback(
    () => setLangState((current) => (current === "en" ? "zh" : "en")),
    [],
  );

  const value = useMemo<I18nValue>(
    () => ({ lang, t: RESOURCES[lang], setLang, toggleLang }),
    [lang, setLang, toggleLang],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (value === null) {
    throw new Error("useI18n must be used inside I18nProvider");
  }
  return value;
}

export function useT(): Messages {
  return useI18n().t;
}

export function format(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key: string) =>
    key in values ? String(values[key]) : `{{${key}}}`,
  );
}
