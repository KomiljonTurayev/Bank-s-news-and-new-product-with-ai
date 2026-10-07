import { useI18n } from "@/shared/lib/i18n/i18n-context";

import ProductForm from "./product-form";
import ProductResult from "./product-result";

// "Yangi mahsulot", tahlil natijasi va tahrirlash — app bar'dagi Mahsulotlar
// ro'yxati ustidan ochiladigan qo'shimcha qatlamlar; yopiladi ustdagi app bar orqali.
export default function ProductScreen({
  subView,
  productId,
}: Readonly<{
  subView: "form" | "result" | "edit";
  productId?: number;
}>) {
  const { t } = useI18n();

  return (
    <div className="screen-overlay">
      <div className="screen-head">
        <h2>{t(subView === "edit" ? "nav_edit_product" : "nav_new_product")}</h2>
      </div>
      <div className="screen-body pp-screen-body">
        {subView === "result" ? (
          <ProductResult id={productId!} />
        ) : (
          <ProductForm editId={subView === "edit" ? productId : undefined} />
        )}
      </div>
    </div>
  );
}
