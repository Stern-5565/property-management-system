/**
 * Internal helper shared by FormField/SelectField/DateField/CurrencyField
 * - not one of Prompt 19's named components itself, just the label/error/
 * aria-wiring those four have in common (id generation, associating the
 * error message via aria-describedby, marking the input aria-invalid).
 * Pulling this out once means fixing an accessibility issue here fixes it
 * for all four field types at once, instead of four places to keep in
 * sync.
 *
 * `children` is a render prop - `(fieldProps) => <input {...fieldProps} />`
 * - rather than a plain element, so a field type that needs to wrap its
 * input in something else (CurrencyField's currency-symbol prefix) can
 * still put `fieldProps` on the actual <input>, not on a wrapper div.
 */
import { useId } from "react";

export function FieldShell({ label, required, error, children }) {
  const id = useId();
  const errorId = `${id}-error`;

  const fieldProps = {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error ? errorId : undefined,
    required,
  };

  return (
    <label className="form-field" htmlFor={id}>
      <span>
        {label}
        {required && (
          <span aria-hidden="true" className="form-field__required">
            {" "}
            *
          </span>
        )}
      </span>
      {children(fieldProps)}
      {error && (
        <span id={errorId} className="form-field__error" role="alert">
          {error}
        </span>
      )}
    </label>
  );
}
