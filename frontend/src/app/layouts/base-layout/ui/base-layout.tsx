import { Outlet } from "react-router-dom";

import { Header } from "@/widgets/header";
import { Footer } from "@/widgets/footer";

export default function BaseLayout() {
  return (
    <>
      <div className="bg-mesh" />
      <Header />
      <main className="container">
        <Outlet />
      </main>
      <Footer />
    </>
  );
}
