import { useLayoutEffect, useRef, useState } from "react";

export const NP_MAX_AMOUNT = 1_000_000_000; // 1 milliard — summa maydonlari undan oshmasligi kerak

// Qo'lda guruhlash: /\B(?=(?:\d{3})+$)/g har bir pozitsiyada qator oxirigacha
// tekshiradi — polinomial vaqt (Sonar S8786). Bu sikl chiziqli va faqat
// raqamlardan iborat qatorlar uchun eski regex bilan bir xil natija beradi.
function groupDigits(digits: string) {
  let out = "";
  for (let i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 === 0) out += " ";
    out += digits[i];
  }
  return out;
}

// Katta summalarni o'qish oson bo'lishi uchun (masalan "50000000" emas,
// "50 000 000") foydalanuvchi kiritayotganda minglik guruhlarga bo'lib
// formatlanadi. Kursor pozitsiyasi "kursordan oldingi RAQAMLAR soni"ga
// qarab tiklanadi — shu bois foydalanuvchi qatorning istalgan joyida
// tahrirlasa ham kursor to'g'ri joyda qoladi.
export function useAmountField(initialDigits = "") {
  const [digits, setDigits] = useState(initialDigits);
  const inputRef = useRef<HTMLInputElement>(null);
  const pendingCursorRef = useRef<{ digitsBeforeCursor: number } | null>(null);

  useLayoutEffect(() => {
    const pending = pendingCursorRef.current;
    if (!pending || !inputRef.current) return;
    pendingCursorRef.current = null;
    const grouped = groupDigits(digits);
    let pos = 0;
    let seen = 0;
    while (pos < grouped.length && seen < pending.digitsBeforeCursor) {
      if (/\d/.test(grouped[pos])) seen++;
      pos++;
    }
    try {
      inputRef.current.setSelectionRange(pos, pos);
    } catch {
      // ba'zi input turlarida selection range o'rnatib bo'lmaydi
    }
  }, [digits]);

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const input = e.target;
    const digitsBeforeCursor = input.value
      .slice(0, input.selectionStart ?? 0)
      .replace(/\D/g, "").length;
    let next = input.value.replace(/\D/g, "").replace(/^0+(?=\d)/, "");
    if (next && Number(next) > NP_MAX_AMOUNT) next = String(NP_MAX_AMOUNT);
    pendingCursorRef.current = { digitsBeforeCursor };
    setDigits(next);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "-" || e.key === "+") e.preventDefault();
  }

  function reset(nextDigits = "") {
    setDigits(nextDigits);
  }

  return {
    displayValue: groupDigits(digits),
    numericValue: digits ? Number.parseFloat(digits) : null,
    inputRef,
    onChange,
    onKeyDown,
    reset,
  };
}
