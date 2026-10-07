import { useRouteError } from "react-router-dom";

import { ErrorFallback } from "./error-fallback";

export const RouteError = () => {
  const error = useRouteError();
  return <ErrorFallback error={error} reset={() => window.location.reload()} />;
};
