// ═══════════════════════════════════════════════════════════════════
// API SO'ROVLARI
// ═══════════════════════════════════════════════════════════════════
function apiUrl(path: string): string {
  return `${import.meta.env.VITE_API_BASE_URL ?? ""}${path}`;
}

export function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(apiUrl(path), init);
}

async function loadJSON(path: string): Promise<any> {
  const url = apiUrl(path);
  const res = await apiFetch(path);
  if (!res.ok) {
    // `.status`ni xatoga biriktirib qo'yamiz — chaqiruvchi 404 kabi
    // holatlarni boshqa xatolardan (tarmoq, 5xx) ajrata olsin.
    const err = new Error(`${url} -> ${res.status}`) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// ── GET keshi ────────────────────────────────────────────────────────
// Ekranlar almashganda ma'lumot qaytadan so'ralmaydi: bu Map modul bilan
// birga yashaydi, ya'ni uning hayoti — sahifa sessiyasi. Keshni yagona
// yo'l bilan yitamiz: sahifa qayta yuklanganda (modul qayta ishga tushadi),
// invalidateJsonCache() chaqirilganda (mahsulot yaratildi/tahrirlandi/
// o'chirildi) yoki resetSessionCaches() bilan (quyida).
const jsonCache = new Map<string, unknown>();
const jsonInflight = new Map<string, Promise<any>>();

// Kesh epochasi + ro'yxatdan o'tgan keshlar. resetSessionCaches() bizning
// Map'mizni va RO'YXATDAN O'TGAN boshqa keshlarni (QueryClient,
// CurrencyProvider ref'lar) birga tozalaydi.
let cacheEpoch = 0;
const sessionCacheClearers = new Set<() => void>();

export function registerSessionCache(clear: () => void): () => void {
  sessionCacheClearers.add(clear);
  return () => sessionCacheClearers.delete(clear);
}

export function resetSessionCaches(): void {
  cacheEpoch++;
  jsonCache.clear();
  jsonInflight.clear();
  // Set'ni to'g'ridan-to'g'ri aylantiramiz: iteratsiya davomidagi delete xavfsiz.
  for (const clear of sessionCacheClearers) clear();
}

export function invalidateJsonCache(prefix: string): void {
  for (const key of jsonCache.keys()) {
    if (key.startsWith(prefix)) jsonCache.delete(key);
  }
}

// Har bir chaqiruvga alohida nusxa beriladi: chaqiruvchi ro'yxatni o'rnida
// sarlasa yoki daraxt qurib obyektga maydon qo'shsa, keshdagi manba (va u
// bilan ishlayotgan qo'shni komponent) buzilmaydi.
export function fetchJSON(path: string): Promise<any> {
  const cached = jsonCache.get(path);
  if (cached !== undefined) return Promise.resolve(structuredClone(cached));

  const pending = jsonInflight.get(path);
  if (pending !== undefined) return pending.then(v => structuredClone(v));

  const epoch = cacheEpoch;
  const request: Promise<any> = loadJSON(path).then(
    value => {
      if (jsonInflight.get(path) === request) jsonInflight.delete(path);
      // Sessiya so'rov ketayotganda almashgan bo'lsa, eski foydalanuvchining
      // javobini yangi sessiya keshiga yozmaymiz (kick race).
      if (epoch === cacheEpoch) jsonCache.set(path, value);
      return value;
    },
    error => {
      // Xato keshlanmaydi — keyingi chaqiruv so'rovni qayta urinishi kerak.
      if (jsonInflight.get(path) === request) jsonInflight.delete(path);
      throw error;
    },
  );
  jsonInflight.set(path, request);
  return request.then(v => structuredClone(v));
}
