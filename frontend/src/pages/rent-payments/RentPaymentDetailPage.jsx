/**
 * GET /api/rent-payments/{id}, plus the record-payment and cancel
 * actions. AmountDue/AmountPaid/AmountOutstanding are shown as three
 * separate, clearly-labeled fields (Prompt 22: "clearly distinguish
 * amount due, amount paid and amount outstanding") rather than folded
 * into one summary line.
 *
 * Edit link only shows while AmountPaid is still 0 and the payment isn't
 * Cancelled, mirroring update_payment's own checks exactly (see
 * rent_payment_service.py) - once any money is recorded, correcting the
 * obligation itself is no longer a plain edit.
 *
 * The record-payment mini-form is inline here rather than a separate
 * page/route: it's a small, repeatable action (multiple partial payments
 * accumulate toward AmountDue - see rentPaymentService.js), not a
 * distinct resource with its own detail view. It's hidden once the
 * payment is Paid or Cancelled - the backend doesn't actually block
 * recording more money against an already-Paid payment, but there's no
 * legitimate reason to invite an accidental overpayment through the UI.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { CurrencyField } from "../../components/CurrencyField";
import { DateField } from "../../components/DateField";
import { SelectField } from "../../components/SelectField";
import { FormField } from "../../components/FormField";
import { ConfirmationDialog } from "../../components/ConfirmationDialog";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_RENT_PAYMENTS } from "../../constants/roles";
import { PAYMENT_METHOD_OPTIONS } from "../../constants/rentPaymentOptions";
import { getPayment, recordPayment, cancelPayment } from "../../services/rentPaymentService";
import { getErrorMessage } from "../../utilities/apiError";

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

const BLANK_RECORD_FORM = { AmountPaid: "", PaymentDate: "", PaymentMethod: "", Notes: "" };

function validateRecordForm(form) {
  const errors = {};
  if (form.AmountPaid === "" || Number(form.AmountPaid) <= 0) {
    errors.AmountPaid = "Enter an amount greater than 0.";
  }
  if (!form.PaymentMethod) {
    errors.PaymentMethod = "Choose a payment method.";
  }
  return errors;
}

export function RentPaymentDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_RENT_PAYMENTS);
  const navigate = useNavigate();
  const location = useLocation();

  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  const [recordForm, setRecordForm] = useState(BLANK_RECORD_FORM);
  const [recordErrors, setRecordErrors] = useState({});
  const [recordSubmitting, setRecordSubmitting] = useState(false);
  const [recordError, setRecordError] = useState(null);

  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelSubmitting, setCancelSubmitting] = useState(false);
  const [cancelError, setCancelError] = useState(null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadPayment = useCallback(() => {
    setLoading(true);
    setError(null);
    getPayment(id)
      .then(setPayment)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadPayment();
  }, [loadPayment]);

  function updateRecordField(field) {
    return (event) => setRecordForm((prev) => ({ ...prev, [field]: event.target.value }));
  }

  function handleRecordPayment(event) {
    event.preventDefault();
    const validationErrors = validateRecordForm(recordForm);
    setRecordErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setRecordSubmitting(true);
    setRecordError(null);
    recordPayment(id, {
      amountPaid: recordForm.AmountPaid,
      paymentDate: recordForm.PaymentDate || null,
      paymentMethod: recordForm.PaymentMethod,
      notes: recordForm.Notes || null,
    })
      .then(() => {
        setToast("Payment recorded.");
        setRecordForm(BLANK_RECORD_FORM);
        loadPayment();
      })
      .catch((err) => setRecordError(getErrorMessage(err)))
      .finally(() => setRecordSubmitting(false));
  }

  function handleConfirmCancel() {
    setCancelSubmitting(true);
    setCancelError(null);
    cancelPayment(id)
      .then(() => {
        setToast("Payment cancelled.");
        loadPayment();
      })
      .catch((err) => setCancelError(getErrorMessage(err)))
      .finally(() => {
        setCancelDialogOpen(false);
        setCancelSubmitting(false);
      });
  }

  if (loading) {
    return <LoadingSpinner label="Loading payment…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadPayment} />;
  }

  const canEdit = payment.PaymentStatus !== "Cancelled" && Number(payment.AmountPaid) === 0;
  const canRecordPayment = payment.PaymentStatus !== "Cancelled" && payment.PaymentStatus !== "Paid";
  const canCancel = payment.PaymentStatus !== "Cancelled";

  return (
    <div>
      <PageHeader
        title={payment.PaymentReference}
        actions={
          canManage &&
          canEdit && (
            <Link to={`/rent-payments/${id}/edit`} className="button button--secondary">
              Edit
            </Link>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="detail-card">
        <StatusBadge status={payment.PaymentStatus} />

        <div className="detail-grid">
          <Field label="Property" value={payment.PropertyReference} />
          <Field label="Tenant" value={payment.TenantName} />
          <Field
            label="Tenancy"
            value={
              <Link to={`/tenancies/${payment.TenancyId}`}>{payment.AgreementReference ?? `#${payment.TenancyId}`}</Link>
            }
          />
          <Field label="Due date" value={payment.DueDate} />
          <Field label="Amount due" value={`£${payment.AmountDue}`} />
          <Field label="Amount paid" value={`£${payment.AmountPaid}`} />
          <Field label="Amount outstanding" value={`£${payment.AmountOutstanding}`} />
          <Field label="Payment date" value={payment.PaymentDate} />
          <Field label="Payment method" value={payment.PaymentMethod} />
          <Field label="External reference" value={payment.ExternalReference} />
          <Field label="Notes" value={payment.Notes} />
        </div>

        {canManage && canRecordPayment && (
          <>
            <h2 className="detail-card__subheading">Record a payment</h2>
            {recordError && <ErrorMessage message={recordError} />}
            <form onSubmit={handleRecordPayment} noValidate>
              <div className="form-grid">
                <CurrencyField
                  label="Amount paid"
                  name="AmountPaid"
                  value={recordForm.AmountPaid}
                  onChange={updateRecordField("AmountPaid")}
                  required
                  error={recordErrors.AmountPaid}
                />
                <DateField
                  label="Payment date (optional - defaults to today)"
                  name="PaymentDate"
                  value={recordForm.PaymentDate}
                  onChange={updateRecordField("PaymentDate")}
                />
                <SelectField
                  label="Payment method"
                  name="PaymentMethod"
                  value={recordForm.PaymentMethod}
                  onChange={updateRecordField("PaymentMethod")}
                  placeholder="Choose a method"
                  options={PAYMENT_METHOD_OPTIONS}
                  required
                  error={recordErrors.PaymentMethod}
                />
                <div className="form-field--full">
                  <FormField label="Notes" name="Notes" value={recordForm.Notes} onChange={updateRecordField("Notes")} />
                </div>
              </div>
              <div className="form-card__actions">
                <button type="submit" className="button" disabled={recordSubmitting}>
                  {recordSubmitting ? "Recording…" : "Record payment"}
                </button>
              </div>
            </form>
          </>
        )}

        {canManage && canCancel && (
          <>
            <div className="detail-card__actions">
              <button type="button" className="button button--danger" onClick={() => setCancelDialogOpen(true)}>
                Cancel payment
              </button>
            </div>
            {cancelError && <ErrorMessage message={cancelError} />}
          </>
        )}

        {payment.PaymentStatus === "Cancelled" && <p>This payment has been cancelled.</p>}
      </div>

      <ConfirmationDialog
        open={cancelDialogOpen}
        title="Cancel this payment?"
        message="This cannot be undone. The obligation will be marked Cancelled and excluded from outstanding/overdue totals; any money already recorded stays on the record."
        confirmLabel="Cancel payment"
        cancelLabel="Go back"
        danger
        confirmDisabled={cancelSubmitting}
        onCancel={() => setCancelDialogOpen(false)}
        onConfirm={handleConfirmCancel}
      />

      <p>
        <Link to="/rent-payments">← Back to rent payments</Link>
      </p>
    </div>
  );
}
