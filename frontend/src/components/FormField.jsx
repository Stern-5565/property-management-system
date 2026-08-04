/**
 * Labeled text/email/password/etc. input - the default field type for
 * every plain-text form value across every module (Landlord's
 * AddressLine1, Tenant's FirstName, ...). See FieldShell for the shared
 * label/error/accessibility wiring.
 */
import { FieldShell } from "./FieldShell";

export function FormField({ label, name, value, onChange, type = "text", required, error, placeholder }) {
  return (
    <FieldShell label={label} required={required} error={error}>
      {(fieldProps) => (
        <input
          {...fieldProps}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="form-field__input"
        />
      )}
    </FieldShell>
  );
}
