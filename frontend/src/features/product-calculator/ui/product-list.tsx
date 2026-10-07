import { useEffect, useRef, useState } from "react";
import { notifications } from "@mantine/notifications";

import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useOpenScreen } from "@/shared/lib/nav/use-open-screen";
import { fetchJSON, apiFetch, invalidateJsonCache } from "@/shared/api/base";

import { productTypeLabel, categoryLabel } from "../lib/product-labels";
import AiAdvisor from "./ai-advisor";

type Product = {
  id: number;
  name: string;
  rate: number;
  purpose: string | null;
  term_months: number | null;
  bank_name: string | null;
  category: string | null;
  product_type: string;
};

function deleteFailMessage(status: number, t: (key: string, vars?: any) => string): string {
  if (status === 422) return t("delete_error_invalid_msg");
  if (status === 429) return t("delete_error_rate_msg");
  return t("delete_error_server_msg", { status });
}

const CONFIRM_MS = 4000;

export default function ProductList() {
  const { t, tn } = useI18n();
  const { openChild } = useOpenScreen();
  const [products, setProducts] = useState<Product[] | null>(null);
  const [error, setError] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDelId, setConfirmDelId] = useState<number | null>(null);
  const reqSeq = useRef(0);
  const confirmTimer = useRef<number | null>(null);

  const reload = () => {
    const seq = ++reqSeq.current;
    setError(false);
    fetchJSON("/api/products")
      .then(data => {
        if (seq === reqSeq.current) setProducts(data);
      })
      .catch(() => {
        if (seq === reqSeq.current) setError(true);
      });
  };

  useEffect(() => {
    reload();
    // Kechikkan javob qayta o'rnatilganda yoki yangiroq yuklanish ustiga
    // tushib ro'yxatni eskirtmasligi uchun navbat raqamini yopamiz.
    return () => {
      reqSeq.current += 1;
    };
  }, []);

  // AI maslahatchisidan pasport saqlanganda ro'yxat yangilansin.
  useEffect(() => {
    const onChanged = () => reload();
    window.addEventListener("products:changed", onChanged);
    return () => window.removeEventListener("products:changed", onChanged);
  }, []);

  useEffect(
    () => () => {
      if (confirmTimer.current !== null) window.clearTimeout(confirmTimer.current);
    },
    [],
  );

  const disarmDelete = () => {
    if (confirmTimer.current !== null) window.clearTimeout(confirmTimer.current);
    confirmTimer.current = null;
    setConfirmDelId(null);
  };

  async function handleDelete(id: number) {
    if (deletingId !== null) return;
    setDeletingId(id);
    try {
      const response = await apiFetch(`/api/products/${id}`, { method: "DELETE" });
      if (response.ok) {
        notifications.show({
          title: t("delete_success_title"),
          message: t("delete_success_msg"),
          color: "green",
          autoClose: 4000,
        });
      } else if (response.status !== 404) {
        // 404 — mahsulot allaqachon o'chirilgan; quyidagi reload() ro'yxatni
        // to'g'irlaydi, foydalanuvchini asossiz hayajonlantirmaymiz.
        notifications.show({
          title: t("delete_error_title"),
          message: deleteFailMessage(response.status, t),
          color: "red",
          autoClose: 5000,
        });
      }
    } catch {
      notifications.show({
        title: t("delete_error_title"),
        message: t("delete_error_offline_msg"),
        color: "red",
        autoClose: 5000,
      });
    } finally {
      setDeletingId(null);
    }
    // Ro'yxat endi eskirgan — keshdagi javobni tushirib, reload()ni
    // haqiqiy so'rovga majburlaymiz.
    invalidateJsonCache("/api/products");
    reload();
  }

  let listBody: React.ReactNode = null;
  if (error) {
    listBody = <p className="empty-note">{t("products_list_error")}</p>;
  } else if (products === null) {
    listBody = <p className="empty-note">{t("bank_grid_loading")}</p>;
  } else if (products.length === 0) {
    listBody = <p className="empty-note">{t("no_products_yet")}</p>;
  } else {
    listBody = products.map(p => {
      const badge = p.category ? categoryLabel(p.category, t) : productTypeLabel(p.product_type, t);
      return (
        <article className="pp-card-item" key={p.id}>
          <div className="pp-card-item-actions">
            <button
              className="cp-edit"
              title={t("edit_btn")}
              onClick={e => {
                e.stopPropagation();
                openChild(`/products/${p.id}/edit`);
              }}>
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true">
                <path d="M4 20h4L20 8l-4-4L4 16v4ZM14.5 5.5l4 4" />
              </svg>
            </button>
            <button
              className={`cp-delete${confirmDelId === p.id ? " arm-del" : ""}`}
              title={t("delete_btn")}
              disabled={deletingId === p.id}
              aria-pressed={confirmDelId === p.id}
              onBlur={() => {
                if (confirmDelId === p.id) disarmDelete();
              }}
              onClick={e => {
                e.stopPropagation();
                if (deletingId !== null) return;
                if (confirmDelId === p.id) {
                  disarmDelete();
                  handleDelete(p.id);
                } else {
                  setConfirmDelId(p.id);
                  if (confirmTimer.current !== null) window.clearTimeout(confirmTimer.current);
                  confirmTimer.current = window.setTimeout(disarmDelete, CONFIRM_MS);
                }
              }}>
              {confirmDelId === p.id ? (
                t("delete_confirm_btn")
              ) : (
                <svg
                  viewBox="0 0 24 24"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true">
                  <path d="M4 7h16M9.5 7V4.8h5V7M6.5 7l.9 13.2h9.2L17.5 7M10 10.8v5.8M14 10.8v5.8" />
                </svg>
              )}
            </button>
          </div>
          {/* Butun kartochka — haqiqiy tugma (Enter/Space brauzerda o'zi ishlaydi).
              Tahrirlash/o'chirish tugmalari ichma-ich bo'lmasligi uchun ustida
              qolgan alohida element; vizual ko'rinish .pp-card-item ostki qatlami
              va quyidagi reset uslublar bilan oldingidek. */}
          <button
            type="button"
            className="pp-card-item-open"
            style={{
              display: "block",
              width: "100%",
              padding: 0,
              border: 0,
              background: "transparent",
              textAlign: "left",
              color: "inherit",
              cursor: "inherit",
              lineHeight: "inherit",
            }}
            onClick={() => openChild(`/products/${p.id}`)}>
            <div className="pp-card-item-badge">
              <span className="pp-pill">{badge}</span>
              {p.bank_name && <span className="pp-card-item-bank">· {p.bank_name}</span>}
            </div>
            <h4 className="pp-card-item-name">{p.name}</h4>
            <p className="pp-card-item-purpose">{p.purpose ? p.purpose : "—"}</p>
            <div className="pp-card-item-foot">
              <span className="pp-card-item-stats">
                <b>{p.rate}%</b> {p.term_months ? `${p.term_months} ${t("months_suffix")}` : ""}
              </span>
              <span className="pp-card-item-link">↗ {t("pp_analysis_ready")}</span>
            </div>
          </button>
        </article>
      );
    });
  }

  return (
    <div className="screen-overlay">
      <div className="screen-head">
        <h2>{t("pp_list_title")}</h2>
      </div>
      <div className="screen-body pp-screen-body">
        <div className="pp-page-head">
          <div>
            <p className="pp-page-sub">{t("pp_page_sub")}</p>
          </div>
          <button type="button" className="btn-primary" onClick={() => openChild("/products/new")}>
            <svg
              viewBox="0 0 24 24"
              width="15"
              height="15"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>
            <span>{t("pp_new_cta")}</span>
          </button>
        </div>

        <AiAdvisor />

        <div className="pp-list-section">
          {products && products.length > 0 && (
            <p className="pp-list-count">{tn("pp_product_count", products.length)}</p>
          )}
          <div className="pp-cards">{listBody}</div>
        </div>
      </div>
    </div>
  );
}
