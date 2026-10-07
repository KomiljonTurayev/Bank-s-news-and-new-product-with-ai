import { RouterProvider } from "react-router-dom";
import type { JSX } from "react";

import { router } from "@/app/routing/app-router";
import { withProviders } from "@/app/providers";

const _Root = (): JSX.Element => <RouterProvider router={router} />;

export const Root = withProviders(_Root);
