import { errorMessage } from "./error-message";

type Props = {
  error: unknown;
};

// MantineProvider ham ishlamay qolgan holat uchun oxirgi chegara —
// shu bois bu yerda Mantine yoki birorta kontekst hook'i ishlatilmaydi.
export const BootErrorFallback = ({ error }: Props) => {
  const message = errorMessage(error);

  return (
    <div
      style={{
        maxWidth: 560,
        margin: "96px auto",
        padding: "0 24px",
        fontFamily: "system-ui, sans-serif",
      }}>
      <h2 style={{ marginBottom: 12 }}>Nimadir xato ketdi</h2>
      <p
        style={{
          padding: "10px 14px",
          borderRadius: 8,
          background: "#fdeceb",
          color: "#c0392b",
          fontSize: 14,
          wordBreak: "break-word",
        }}>
        {message}
      </p>
      <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
        <button type="button" onClick={() => window.location.reload()}>
          Qayta urinish
        </button>
        <button type="button" onClick={() => (window.location.href = "/")}>
          Bosh sahifa
        </button>
      </div>
    </div>
  );
};
