export default function ErrorBanner({ message, onDismiss }) {
  if (!message) {
    return null;
  }

  return (
    <div className="error-banner" role="status">
      <span>{message}</span>
      <button type="button" onClick={onDismiss} aria-label="Dismiss error">
        x
      </button>
    </div>
  );
}
