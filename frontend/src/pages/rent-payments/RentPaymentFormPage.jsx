/**
 * Shared create/edit form - POST /api/rent-payments; PUT is only
 * accepted while AmountPaid is still 0 and the payment isn't Cancelled
 * (RentPaymentDetailPage only shows the Edit link in that state - see
 * its own docstring). Tenancy selector loads options the same direct
 * pageSize:100 way PropertyFormPage's landlord dropdown does, labeled
 * with property+tenant+status so a tenancy is identifiable without
 * needing its raw ID.
 *
 * Client-side validation only covers the cheap static rules (required
 * fields, AmountDue >= 0) - duplicate PaymentReference detection is left
 * entirely to the server's message, same convention as every other
 * module's form.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SelectField } from "../../components/SelectField";
import { DateField } from "../../components/DateField";
import { CurrencyField } from "../../components/CurrencyField";
import { getPayment, createPayment, updatePayment } from "../../services/rentPaymentService";
import { listTenancies } from "../../services/tenancyService";
import { getErrorMessage } from "../../utilities/apiError";

const BLANK_FORM = {
  TenancyId: "",
  PaymentReference: "",
  DueDate: "",
  AmountDue: "",
  ExternalReference: "",
  Notes: "",
};

function validate(form) {
  const errors = {};
  if (!form.TenancyId) errors.TenancyId = "Choose a tenancy.";
  if (!form.PaymentReference.trim()) errors.PaymentReference = "Payment reference is required.";
  if (!form.DueDate) errors.DueDate = "Due date is required.";
  if (form.AmountDue === "" || Number(form.AmountDue) < 0) {
    errors.AmountDue = "Enter an amount of 0 or more.";
  }
  return errors;
}

function toPayload(form) {
  const emptyToNull = (value) => (value.trim() === "" ? null : value.trim());
  return {
    TenancyId: Number(form.TenancyId),
    PaymentReference: form.PaymentReference.trim(),
    DueDate: form.DueDate,
    AmountDue: form.AmountDue.trim(),
    ExternalReference: emptyToNull(form.ExternalReference),
    Notes: emptyToNull(form.Notes),
  };
}

export function RentPaymentFormPage() {
  const { id } = useParams();
  const isEdit = id !== undefined;
  const navigate = useNavigate();

  const [form, setForm] = useState(BLANK_FORM);
  const [tenancyOptions, setTenancyOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const tenanciesPromise = listTenancies({ pageSize: 100 }).then((data) =>
      setTenancyOptions(
        data.items.map((t) => ({
          value: String(t.TenancyId),
          label: `${t.PropertyReference} — ${t.TenantName} (${t.TenancyStatus})`,
        })),
      ),
    );
    const paymentPromise = isEdit
      ? getPayment(id).then((payment) =>
          setForm({
            TenancyId: String(payment.TenancyId),
            PaymentReference: payment.PaymentReference,
            DueDate: payment.DueDate,
            AmountDue: String(payment.AmountDue),
            ExternalReference: payment.ExternalReference ?? "",
            Notes: payment.Notes ?? "",
          }),
        )
      : Promise.resolve();

    Promise.all([tenanciesPromise, paymentPromise])
      .catch((err) => setLoadError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id, isEdit]);

  function updateField(field) {
    return (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    const validationErrors = validate(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    const payload = toPayload(form);
    const request = isEdit ? updatePayment(id, payload) : createPayment(payload);
    request
      .then((payment) => {
        navigate(`/rent-payments/${payment.RentPaymentId}`, {
          state: { toast: isEdit ? "Payment updated." : "Rent payment created." },
        });
      })
      .catch((err) => setSubmitError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  if (loading) {
    return <LoadingSpinner label="Loading…" />;
  }

  if (loadError) {
    return <ErrorMessage message={loadError} />;
  }

  return (
    <div>
      <PageHeader title={isEdit ? "Edit rent payment" : "New rent payment"} />

      {submitError && <ErrorMessage message={submitError} />}

      <form className="form-card" onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          <div className="form-field--full">
            <SelectField
              label="Tenancy"
              name="TenancyId"
              value={form.TenancyId}
              onChange={updateField("TenancyId")}
              placeholder="Choose a tenancy"
              options={tenancyOptions}
              required
              error={errors.TenancyId}
            />
          </div>
          <FormField
            label="Payment reference"
            name="PaymentReference"
            value={form.PaymentReference}
            onChange={updateField("PaymentReference")}
            required
            error={errors.PaymentReference}
          />
          <DateField
            label="Due date"
            name="DueDate"
            value={form.DueDate}
            onChange={updateField("DueDate")}
            required
            error={errors.DueDate}
          />
          <CurrencyField
            label="Amount due"
            name="AmountDue"
            value={form.AmountDue}
            onChange={updateField("AmountDue")}
            required
            error={errors.AmountDue}
          />
          <FormField
            label="External reference"
            name="ExternalReference"
            value={form.ExternalReference}
            onChange={updateField("ExternalReference")}
          />
          <div className="form-field--full">
            <FormField label="Notes" name="Notes" value={form.Notes} onChange={updateField("Notes")} />
          </div>
        </div>

        <div className="form-card__actions">
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create payment"}
          </button>
          <button type="button" className="button button--secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
