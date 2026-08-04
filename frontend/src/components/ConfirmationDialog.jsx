/**
 * Modal "are you sure?" prompt - for destructive/irreversible actions
 * (deactivating a landlord, cancelling a tenancy, ...) across every
 * module. Deliberately NOT a full focus-trap implementation (no
 * third-party dialog library) - "avoid unnecessary complexity" per the
 * scope doc's Prompt 19 requirements. What it does do: moves focus to
 * Cancel on open (a safe default so an accidental Enter press doesn't
 * confirm a destructive action), closes on Escape, and closes on
 * backdrop click - covering the accessibility cases that matter most for
 * a dialog this simple, without pulling in a dependency for the rest.
 */
import { useEffect, useRef } from "react";

export function ConfirmationDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  danger = false,
}) {
  const cancelButtonRef = useRef(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    cancelButtonRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onCancel();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" onClick={onCancel}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirmation-dialog-title"
        aria-describedby="confirmation-dialog-message"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="confirmation-dialog-title" className="dialog__title">
          {title}
        </h2>
        <p id="confirmation-dialog-message">{message}</p>
        <div className="dialog__actions">
          <button type="button" ref={cancelButtonRef} className="button button--secondary" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={danger ? "button button--danger" : "button"}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
