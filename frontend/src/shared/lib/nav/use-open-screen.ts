import { useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const HOME = "/";

// Ekranlar (MPL / Mahsulotlar) home ustida ochiladi: home'dan bir marta push
// qilinadi, bo'lim ichidagi chuqurlashish shu slotning ustiga yoziladi. Ekran
// yopilganda tarix replace bilan to'ldirilmaydi (aks holda har ochish-yopish
// history'ga bitta yozuv qo'shib, "orqaga" ni bir necha marta bosishga
// majbur qilardi), balki o'sha asosiy home yozuviga qaytiladi — keyingi
// ochish eski yozuvlarni ustiga yozgani uchun tarix o'smaydi.
let homeBase: number | null = null;

const historyIdx = (): number | null =>
  (window.history.state as { idx?: number } | null)?.idx ?? null;

export function useOpenScreen() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const atHome = pathname === HOME;

  const open = useCallback(
    (to: string) => {
      if (to === pathname) return;
      if (atHome) homeBase = historyIdx() ?? 0;
      navigate(to, { replace: !atHome });
    },
    [atHome, navigate, pathname],
  );

  // Bo'lim Ichida chuqurlashish (ro'yxat -> konkret mahsulot): bu yerdagi
  // o'tish tarixga yoziladi, chunki "orqaga" mantiqan birinchi bosqichga —
  // masalan ro'yxatga — qaytishi kutiladi.
  const openChild = useCallback(
    (to: string) => {
      if (to === pathname) return;
      navigate(to);
    },
    [navigate, pathname],
  );

  // Ichki bosqichdan bir tepaga qaytish. Tarixda oldingi yozuv bo'lsa shunga
  // qaytamiz (ro'yxat saqlanadi), bo'lmasa — berilgan manzilga o'tamiz
  // (masalan sahifaga to'g'ridan-to'g'ri kirilganda).
  const goBackOr = useCallback(
    (to: string) => {
      const idx = (window.history.state as { idx?: number } | null)?.idx;
      if (typeof idx === "number" && idx > 0) navigate(-1);
      else navigate(to, { replace: !atHome });
    },
    [atHome, navigate],
  );

  const goHome = useCallback(() => {
    if (atHome) return;
    const idx = historyIdx();
    // Home ochiq slotni replace qilmaymiz: replace tarixni o'stirardi (har
    // ochish-yopishda bitta yozuv qolardi va "orqaga" bir necha marta
    // bosilardi). Ustidagi slotlar soni kadarmiga orqaga qaytamiz.
    if (idx !== null && homeBase !== null && idx > homeBase) navigate(homeBase - idx);
    else navigate(HOME, { replace: true });
  }, [atHome, navigate]);

  return { open, goHome, openChild, goBackOr };
}
