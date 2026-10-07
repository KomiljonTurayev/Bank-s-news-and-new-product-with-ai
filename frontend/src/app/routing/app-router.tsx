import { type JSX, lazy, Suspense, type LazyExoticComponent } from "react";
import { Outlet, createBrowserRouter } from "react-router-dom";

import { RouteError } from "@/shared/ui/error-fallback";

type Component = LazyExoticComponent<() => JSX.Element>;

const BaseLayout = lazy(() => import("@/app/layouts/base-layout"));

const Home: Component = lazy(() => import("@/pages/home"));
const Mpl: Component = lazy(() => import("@/pages/mpl"));
const Products: Component = lazy(() => import("@/pages/products"));
const ProductNew: Component = lazy(() => import("@/pages/product-new"));
const ProductEditPage: Component = lazy(() => import("@/pages/product-edit"));
const ProductResultPage: Component = lazy(() => import("@/pages/product-result"));
const NotFound: Component = lazy(() => import("@/pages/not-found"));

// App bar'dan ochiladigan ekranlar aynan home oynasida ochiladi: home
// mount bo'lib qoladi, ekran uning ustida qatlam bo'lib chiqadi.
const HomeShell = (): JSX.Element => (
  <>
    {/* Ikki alohida chegara: uy qatlamiga biriktirilgan ekran ochilayotganda
        uy (va app bar) o'z holicha ko'rinib turadi. */}
    <Suspense fallback={null}>
      <Home />
    </Suspense>
    <Suspense fallback={null}>
      <Outlet />
    </Suspense>
  </>
);

// `errorElement` router darajasidagi eng yaqin chegara: layout'ning o'zida
// (Header/Footer) ketgan xatolar ichidagi nozik chegaradan YUQORIDA bo'lgani
// uchun shu yerga qadar ko'tariladi. Chegara bo'lmasa router o'zining
// standby "Unexpected Application Error" ekranini ko'rsatardi.
export const router = createBrowserRouter([
  {
    path: "/",
    element: <BaseLayout />,
    errorElement: <RouteError />,
    children: [
      {
        errorElement: <RouteError />,
        children: [
          {
            element: <HomeShell />,
            children: [
              { index: true },
              { path: "mpl", element: <Mpl /> },
              { path: "products", element: <Products /> },
              { path: "products/new", element: <ProductNew /> },
              { path: "products/:id", element: <ProductResultPage /> },
              { path: "products/:id/edit", element: <ProductEditPage /> },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <NotFound />, errorElement: <RouteError /> },
]);
