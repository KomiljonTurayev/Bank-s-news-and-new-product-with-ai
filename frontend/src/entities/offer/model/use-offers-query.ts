import { useQuery } from "@tanstack/react-query";

import { fetchJSON } from "@/shared/api/base";

export function useOffersQuery(product: string, segment: string) {
  return useQuery({
    queryKey: ["rates", "latest", product, segment],
    queryFn: () =>
      fetchJSON(
        `/api/rates/latest?product_type=${encodeURIComponent(product)}&segment=${encodeURIComponent(segment)}`,
      ),
  });
}
