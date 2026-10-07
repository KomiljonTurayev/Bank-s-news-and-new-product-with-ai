import { useParams } from "react-router-dom";

import { ProductScreen } from "@/features/product-calculator";

export default function ProductEdit() {
  const { id } = useParams();

  return <ProductScreen subView="edit" productId={Number(id)} />;
}
