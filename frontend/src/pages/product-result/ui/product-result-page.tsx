import { useParams } from "react-router-dom";

import { ProductScreen } from "@/features/product-calculator";

export default function ProductResultPage() {
  const { id } = useParams();

  return <ProductScreen subView="result" productId={Number(id)} />;
}
