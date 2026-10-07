import {
  QueryClient,
  QueryCache,
  MutationCache,
  QueryClientProvider,
  type Query,
} from "@tanstack/react-query";
import { type ReactNode } from "react";

import { store } from "@/app/store";
import { setError } from "@/shared/model";
import { registerSessionCache } from "@/shared/api/base";

const handleError = (err: unknown) => {
  const message = err instanceof Error ? err.message : "Noma'lum xatolik";
  store.dispatch(setError(message));
};

// Background refetch yiqilganda qo'lida hali ko'rinib turgan ma'lumot bo'lgan
// so'rov uchun qizil alert ko'rsatilmaydi: manba uzilgani foydalanuvchiga
// sahifadagi "eskirgan ma'lumot" ogohlantirishi bilan yetkaziladi.
const handleQueryError = (err: unknown, query: Query) => {
  if (query.state.data !== undefined) return;
  handleError(err);
};

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: handleQueryError }),
  mutationCache: new MutationCache({ onError: handleError }),
  defaultOptions: {
    queries: {
      retry: false,
      throwOnError: false,
    },
  },
});

// Sessiya almashganda react-query keshidagi birinchi foydalanuvchining
// ma'lumotlari (offer/meta — egalik-bo'yicha keladi) keyingi sessiyaga
// o'tib qolmasin. Modul darajasida ro'yxatdan o'tadi: queryClient ham
// butun ilova davomida yashaydi.
registerSessionCache(() => {
  queryClient.clear();
});

export const QueryProvider = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);
