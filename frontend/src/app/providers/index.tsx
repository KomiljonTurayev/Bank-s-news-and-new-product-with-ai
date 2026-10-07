import { type ComponentType, type ErrorInfo, useEffect } from "react";
import { useMantineColorScheme } from "@mantine/core";

import { ThemeProvider, useTheme } from "@/shared/lib/theme/theme-context";
import { ErrorBoundary } from "@/app/providers/ui/error-boundary";
import { ErrorFallback } from "@/shared/ui/error-fallback";
import { QueryProvider } from "@/app/providers/with-query";
import { GlobalErrorNotification } from "@/widgets/global-error-notification";
import { I18nProvider } from "@/shared/lib/i18n/i18n-context";
import { CurrencyProvider } from "@/entities/currency";

import { withMantine } from "./with-mantine";

const handleAppError = (error: unknown, info: ErrorInfo) => {
  console.error("App-level error:", error, info);
};

// Ilova rejimini Mantine rang sxemasiga ulaydi — bildirishnoma va
// Mantine komponentlari ham qorong'u rejimda to'g'ri ko'ringan uchun.
function MantineThemeSync() {
  const { theme } = useTheme();
  const { setColorScheme } = useMantineColorScheme();
  useEffect(() => {
    setColorScheme(theme === "dark" ? "dark" : "light");
  }, [theme, setColorScheme]);
  return null;
}

const withOtherProviders = (Component: ComponentType) => () => (
  <ErrorBoundary fallback={ErrorFallback} onError={handleAppError}>
    <QueryProvider>
      <I18nProvider>
        <ThemeProvider>
          <CurrencyProvider>
            <GlobalErrorNotification />
            <MantineThemeSync />
            <Component />
          </CurrencyProvider>
        </ThemeProvider>
      </I18nProvider>
    </QueryProvider>
  </ErrorBoundary>
);

export const withProviders = (Component: ComponentType) =>
  withMantine(withOtherProviders(Component));
