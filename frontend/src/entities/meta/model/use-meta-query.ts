import { useQuery } from "@tanstack/react-query";

import { fetchJSON } from "@/shared/api/base";

export function useMeta() {
  const { data, isFetched } = useQuery({
    queryKey: ["meta"],
    queryFn: () => fetchJSON("/api/meta"),
  });

  return { banks: data?.banks ?? [], loaded: isFetched };
}
