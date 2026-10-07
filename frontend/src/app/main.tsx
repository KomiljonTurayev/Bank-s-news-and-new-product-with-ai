import { createRoot } from "react-dom/client";
import { StrictMode } from "react";
import { Provider } from "react-redux";

import "./index.css";
import { store } from "@/app/store";
import { Root } from "@/app/Root";
import { ErrorBoundary } from "@/app/providers/ui/error-boundary";
import { BootErrorFallback } from "@/shared/ui/error-fallback";

// Eng tashqi chegara: provayderlarning o'zi (Mantine, Query, Redux) qulasa
// ham ilova oq ekran bo'lib qolmaydi.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary fallback={BootErrorFallback}>
      <Provider store={store}>
        <Root />
      </Provider>
    </ErrorBoundary>
  </StrictMode>,
);
