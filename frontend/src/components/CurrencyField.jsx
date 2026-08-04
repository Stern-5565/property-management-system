/**
 * Labeled numeric input with a currency symbol prefix - for every money
 * field across every module (Property's MonthlyRent, RentPayment's
 * AmountDue, MaintenanceRequest's EstimatedCost, ...). `value`/`onChange`
 * carry a plain numeric string; this component only handles the display
 * affordance (the £ prefix, step="0.01", min="0"), not currency
 * formatting/parsing - that's the same "plain data in, plain data out"
 * shape the other field components use, so a module's save handler
 * doesn't need special-case unwrapping for this one field type.
 */
import { FieldShell } from "./FieldShell";

export function CurrencyField({ label, name, value, onChange, required, error, currencySymbol = "£", placeholder }) {
  return (
    <FieldShell label={label} required={required} error={error}>
      {(fieldProps) => (
        <span className="currency-field">
          <span className="currency-field__symbol" aria-hidden="true">
            {currencySymbol}
          </span>
          <input
            {...fieldProps}
            name={name}
            type="number"
            step="0.01"
            min="0"
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            className="form-field__input currency-field__input"
          />
        </span>
      )}
    </FieldShell>
  );
}
