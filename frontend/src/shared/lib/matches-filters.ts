export function matchesFilters(
  code: string,
  name: string,
  { search, compareSet }: { search: string; compareSet: Set<string> },
) {
  const query = search.trim().toLowerCase();
  if (query && !name.toLowerCase().includes(query)) return false;
  if (compareSet.size > 0 && !compareSet.has(code)) return false;
  return true;
}
