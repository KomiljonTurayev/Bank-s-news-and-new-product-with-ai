import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { notifications } from "@mantine/notifications";

import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useOpenScreen } from "@/shared/lib/nav/use-open-screen";
import { apiFetch, invalidateJsonCache } from "@/shared/api/base";

import { productTypeLabel } from "../lib/product-labels";

// ═══════════════════════════════════════════════════════════════════
// AI MAHSULOT MASLAHATCHISI — chat ko'rinishida. Har so'rov backend'ga
// (`POST /api/products/recommend`) alohida ketadi; suhbat tarixi faqat shu
// ekranda yashaydi, tavsiyalar bir bosishda pasport sifatida saqlanadi.
// ═══════════════════════════════════════════════════════════════════

type ProductType = "credit" | "deposit" | "card" | "investment";

type Recommendation = {
  name: string;
  product_type: ProductType;
  category: string | null;
  currency: string;
  rate: number;
  min_amount: number | null;
  max_amount: number | null;
  term_months: number | null;
  initial_payment_pct: number | null;
  target_segment: string;
  purpose: string;
  rationale: string;
  risks: string[];
};

type AdvisorReply = {
  market_count: number;
  model: string;
  market_overview: string;
  recommendations: Recommendation[];
};

type Message =
  | { id: number; role: "user"; text: string; productType: ProductType }
  | { id: number; role: "assistant"; reply: AdvisorReply }
  | { id: number; role: "error"; text: string; retry: { productType: ProductType; goal: string } };

const PRODUCT_TYPES: ProductType[] = ["credit", "deposit", "card", "investment"];

const SUGGESTIONS: { type: ProductType; key: string }[] = [
  { type: "deposit", key: "ai_suggest_youth_deposit" },
  { type: "credit", key: "ai_suggest_mortgage" },
  { type: "card", key: "ai_suggest_cashback" },
  { type: "credit", key: "ai_suggest_business" },
];

const THINKING_STEPS = ["ai_step_reading", "ai_step_comparing", "ai_step_drafting"];

function formatAmount(value: number | null, locale: string): string | null {
  if (value === null) return null;
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value);
}

function SparkIcon({ size = 16 }: Readonly<{ size?: number }>) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden="true">
      <path d="M12 2.5c.4 3.9 1.6 6.2 3.3 7.6 1.4 1.1 3.3 1.6 6.2 1.9-3 .3-4.9.8-6.3 1.9-1.7 1.4-2.8 3.7-3.2 7.6-.4-3.9-1.6-6.2-3.3-7.6-1.4-1.1-3.3-1.6-6.2-1.9 2.9-.3 4.8-.8 6.2-1.9 1.7-1.4 2.9-3.7 3.3-7.6Z" />
      <path
        d="M19 2.8c.2 1.3.6 2 1.2 2.4.4.3 1 .5 1.8.6-.8.1-1.4.3-1.8.6-.6.5-1 1.2-1.2 2.5-.2-1.3-.6-2-1.2-2.5-.4-.3-1-.5-1.8-.6.8-.1 1.4-.3 1.8-.6.6-.4 1-1.1 1.2-2.4Z"
        opacity=".6"
      />
    </svg>
  );
}

function ThinkingBubble() {
  const { t } = useI18n();
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(
      () => setStep(s => Math.min(s + 1, THINKING_STEPS.length - 1)),
      9000,
    );
    return () => window.clearInterval(timer);
  }, []);
  return (
    <div className="ai-row ai-row-assistant" aria-live="polite">
      <div className="ai-avatar">
        <SparkIcon />
      </div>
      <div className="ai-bubble ai-bubble-thinking">
        <span className="ai-dots" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <span className="ai-thinking-text">{t(THINKING_STEPS[step])}</span>
      </div>
    </div>
  );
}

function RecommendationCard({ rec, index }: Readonly<{ rec: Recommendation; index: number }>) {
  const { t, locale } = useI18n();
  const { openChild } = useOpenScreen();
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<number | null>(null);

  const min = formatAmount(rec.min_amount, locale);
  const max = formatAmount(rec.max_amount, locale);
  let amount: string | null = null;
  if (min && max) amount = `${min} – ${max}`;
  else if (min) amount = `${t("ai_from")} ${min}`;
  else if (max) amount = `${t("ai_upto")} ${max}`;

  const specs: { label: string; value: string }[] = [];
  if (rec.term_months)
    specs.push({ label: t("ai_spec_term"), value: `${rec.term_months} ${t("months_suffix")}` });
  if (amount) specs.push({ label: t("ai_spec_amount"), value: `${amount} ${rec.currency}` });
  if (rec.initial_payment_pct !== null)
    specs.push({ label: t("ai_spec_initial"), value: `${rec.initial_payment_pct}%` });

  async function save() {
    if (savedId !== null) {
      openChild(`/products/${savedId}`);
      return;
    }
    setSaving(true);
    try {
      const response = await apiFetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: rec.name,
          product_type: rec.product_type,
          category: rec.category,
          bank_name: null,
          purpose: `${rec.target_segment} — ${rec.purpose}`.slice(0, 300),
          currency: rec.currency,
          rate: rec.rate,
          term_months: rec.term_months ? Math.min(Math.max(rec.term_months, 1), 240) : null,
          min_amount: rec.min_amount,
          max_amount: rec.max_amount,
          initial_payment_pct: rec.initial_payment_pct,
        }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const created = await response.json();
      setSavedId(created.id);
      invalidateJsonCache("/api/products");
      window.dispatchEvent(new Event("products:changed"));
      notifications.show({
        title: t("ai_saved_title"),
        message: rec.name,
        color: "green",
        autoClose: 3500,
      });
    } catch {
      notifications.show({
        title: t("ai_save_error"),
        message: rec.name,
        color: "red",
        autoClose: 5000,
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="ai-rec" style={{ animationDelay: `${index * 90}ms` }}>
      <header className="ai-rec-head">
        <div className="ai-rec-titles">
          <span className="ai-rec-index">{String(index + 1).padStart(2, "0")}</span>
          <div>
            <h4 className="ai-rec-name">{rec.name}</h4>
            <div className="ai-rec-tags">
              <span className="pp-pill">
                {rec.category || productTypeLabel(rec.product_type, t)}
              </span>
              <span className="ai-rec-segment">{rec.target_segment}</span>
            </div>
          </div>
        </div>
        <div className="ai-rec-rate">
          <b>{rec.rate}%</b>
          <span>{t("ai_rate_caption")}</span>
        </div>
      </header>

      {specs.length > 0 && (
        <dl className="ai-rec-specs">
          {specs.map(s => (
            <div key={s.label}>
              <dt>{s.label}</dt>
              <dd>{s.value}</dd>
            </div>
          ))}
        </dl>
      )}

      <p className="ai-rec-purpose">{rec.purpose}</p>

      <div className="ai-rec-why">
        <span className="ai-rec-label">{t("ai_why")}</span>
        <p>{rec.rationale}</p>
      </div>

      {rec.risks.length > 0 && (
        <details className="ai-rec-risks">
          <summary>
            {t("ai_risks")} <span>{rec.risks.length}</span>
          </summary>
          <ul>
            {rec.risks.map(r => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </details>
      )}

      <footer className="ai-rec-foot">
        <button
          type="button"
          className={savedId === null ? "btn-primary ai-rec-save" : "btn-secondary ai-rec-save"}
          disabled={saving}
          onClick={save}>
          {saving && t("ai_saving")}
          {!saving && savedId === null && t("ai_save_cta")}
          {!saving && savedId !== null && `↗ ${t("ai_open_saved")}`}
        </button>
      </footer>
    </article>
  );
}

export default function AiAdvisor() {
  const { t, lang } = useI18n();
  const [productType, setProductType] = useState<ProductType>("deposit");
  const [goal, setGoal] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState(false);
  const nextId = useRef(1);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const thread = threadRef.current;
    if (thread) thread.scrollTo({ top: thread.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  async function ask(type: ProductType, text: string) {
    if (pending) return;
    const trimmed = text.trim();
    setMessages(m => [
      ...m,
      {
        id: nextId.current++,
        role: "user",
        text: trimmed || t("ai_default_ask"),
        productType: type,
      },
    ]);
    setGoal("");
    setPending(true);
    try {
      const response = await apiFetch("/api/products/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_type: type, goal: trimmed || null, count: 3, lang }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === "string" ? body.detail : t("ai_error_generic");
        throw new Error(detail);
      }
      setMessages(m => [...m, { id: nextId.current++, role: "assistant", reply: body }]);
    } catch (err: any) {
      const text =
        err instanceof TypeError ? t("ai_error_offline") : err.message || t("ai_error_generic");
      setMessages(m => [
        ...m,
        { id: nextId.current++, role: "error", text, retry: { productType: type, goal: trimmed } },
      ]);
    } finally {
      setPending(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    ask(productType, goal);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      ask(productType, goal);
    }
  }

  return (
    <section className="ai-advisor" aria-label={t("ai_title")}>
      <header className="ai-head">
        <div className="ai-head-mark">
          <SparkIcon size={20} />
        </div>
        <div className="ai-head-text">
          <h3>{t("ai_title")}</h3>
          <p>{t("ai_subtitle")}</p>
        </div>
        <span className="ai-head-status">
          <i aria-hidden="true" />
          {t("ai_online")}
        </span>
      </header>

      <div className="ai-thread" ref={threadRef}>
        <div className="ai-row ai-row-assistant">
          <div className="ai-avatar">
            <SparkIcon />
          </div>
          <div className="ai-bubble">
            <p>{t("ai_greeting")}</p>
            {messages.length === 0 && (
              <div className="ai-chips">
                {SUGGESTIONS.map(s => (
                  <button
                    key={s.key}
                    type="button"
                    className="ai-chip"
                    disabled={pending}
                    onClick={() => {
                      setProductType(s.type);
                      ask(s.type, t(s.key));
                    }}>
                    {t(s.key)}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {messages.map(msg => {
          if (msg.role === "user") {
            return (
              <div className="ai-row ai-row-user" key={msg.id}>
                <div className="ai-bubble ai-bubble-user">
                  <span className="ai-user-type">{productTypeLabel(msg.productType, t)}</span>
                  <p>{msg.text}</p>
                </div>
              </div>
            );
          }
          if (msg.role === "error") {
            return (
              <div className="ai-row ai-row-assistant" key={msg.id}>
                <div className="ai-avatar ai-avatar-error">!</div>
                <div className="ai-bubble ai-bubble-error">
                  <p>{msg.text}</p>
                  <button
                    type="button"
                    className="ai-chip"
                    disabled={pending}
                    onClick={() => ask(msg.retry.productType, msg.retry.goal)}>
                    ↻ {t("ai_retry")}
                  </button>
                </div>
              </div>
            );
          }
          return (
            <div className="ai-row ai-row-assistant" key={msg.id}>
              <div className="ai-avatar">
                <SparkIcon />
              </div>
              <div className="ai-answer">
                <div className="ai-bubble">
                  <p>{msg.reply.market_overview}</p>
                  <span className="ai-meta">
                    {t("ai_meta", { count: msg.reply.market_count, model: msg.reply.model })}
                  </span>
                </div>
                <div className="ai-recs">
                  {msg.reply.recommendations.map((rec, i) => (
                    <RecommendationCard rec={rec} index={i} key={`${msg.id}-${rec.name}`} />
                  ))}
                </div>
              </div>
            </div>
          );
        })}

        {pending && <ThinkingBubble />}
      </div>

      <form className="ai-composer" onSubmit={onSubmit}>
        <div className="ai-types" role="radiogroup" aria-label={t("ai_type_label")}>
          {PRODUCT_TYPES.map(type => (
            <button
              key={type}
              type="button"
              role="radio"
              aria-checked={productType === type}
              className={`ai-type${productType === type ? " active" : ""}`}
              onClick={() => setProductType(type)}>
              {productTypeLabel(type, t)}
            </button>
          ))}
        </div>
        <div className="ai-input">
          <textarea
            rows={1}
            value={goal}
            maxLength={500}
            placeholder={t("ai_placeholder")}
            onChange={e => setGoal(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <button type="submit" className="ai-send" disabled={pending} title={t("ai_send")}>
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </div>
        <p className="ai-disclaimer">{t("ai_disclaimer")}</p>
      </form>
    </section>
  );
}
