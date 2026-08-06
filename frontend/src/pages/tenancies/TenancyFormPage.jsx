/**
 * Shared create/edit form - POST /api/tenancies always creates a Draft;
 * PUT /api/tenancies/{id} is only accepted while still Draft
 * (TenancyDetailPage only shows the Edit link in that state - see its
 * own docstring). Property/Tenant selectors load active options the same
 * way PropertyFormPage's landlord dropdown does - a direct pageSize:100
 * call, not a new shared abstraction for two call sites.
 *
 * Client-side validation only covers the cheap, static rules
 * (required fields, MonthlyRent > 0, PaymentDueDay 1-28, EndDate after
 * StartDate - mirroring TenancyCreate.validate_date_order) per the scope
 * doc's Prompt 21 instruction not to duplicate backend business-rule
 * validation unnecessarily; overlap conflicts and inactive-property/
 * tenant checks only happen at Activate time on the backend, so they're
 * never checked here.
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
import { getTenancy, createTenancy, updateTenancy } from "../../services/tenancyService";
import { listProperties } from "../../services/propertyService";
import { listTenants } from "../../services/tenantService";
import { getErrorMessage } from "../../utilities/apiError";

const BLANK_FORM = {
  PropertyId: "",
  TenantId: "",
  StartDate: "",
  EndDate: "",
  MonthlyRent: "",
  DepositAmount: "0",
  PaymentDueDay: "1",
  AgreementReference: "",
  Notes: "",
};

function validate(form) {
  const errors = {};
  if (!form.PropertyId) errors.PropertyId = "Choose a property.";
  if (!form.TenantId) errors.TenantId = "Choose a tenant.";
  if (!form.StartDate) errors.StartDate = "Start date is required.";
  if (form.StartDate && form.EndDate && form.EndDate <= form.StartDate) {
    errors.EndDate = "End date must be after the start date.";
  }
  if (form.MonthlyRent === "" || Number(form.MonthlyRent) <= 0) {
    errors.MonthlyRent = "Enter a monthly rent greater than 0.";
  }
  if (form.DepositAmount !== "" && Number(form.DepositAmount) < 0) {
    errors.DepositAmount = "Deposit cannot be negative.";
  }
  const dueDay = Number(form.PaymentDueDay);
  if (form.PaymentDueDay === "" || !Number.isInteger(dueDay) || dueDay < 1 || dueDay > 28) {
    errors.PaymentDueDay = "Enter a whole number between 1 and 28.";
  }
  return errors;
}

function toPayload(form) {
  const emptyToNull = (value) => (value.trim() === "" ? null : value.trim());
  return {
    PropertyId: Number(form.PropertyId),
    TenantId: Number(form.TenantId),
    StartDate: form.StartDate,
    EndDate: form.EndDate === "" ? null : form.EndDate,
    MonthlyRent: form.MonthlyRent.trim(),
    DepositAmount: form.DepositAmount.trim() === "" ? "0.00" : form.DepositAmount.trim(),
    PaymentDueDay: Number(form.PaymentDueDay),
    AgreementReference: emptyToNull(form.AgreementReference),
    Notes: emptyToNull(form.Notes),
  };
}

export function TenancyFormPage() {
  const { id } = useParams();
  const isEdit = id !== undefined;
  const navigate = useNavigate();

  const [form, setForm] = useState(BLANK_FORM);
  const [propertyOptions, setPropertyOptions] = useState([]);
  const [tenantOptions, setTenantOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const propertiesPromise = listProperties({ pageSize: 100, isActive: true }).then((data) =>
      setPropertyOptions(data.items.map((p) => ({ value: String(p.PropertyId), label: p.PropertyReference }))),
    );
    const tenantsPromise = listTenants({ pageSize: 100, isActive: true }).then((data) =>
      setTenantOptions(data.items.map((t) => ({ value: String(t.TenantId), label: `${t.FirstName} ${t.LastName}` }))),
    );
    const tenancyPromise = isEdit
      ? getTenancy(id).then((tenancy) =>
          setForm({
            PropertyId: String(tenancy.PropertyId),
            TenantId: String(tenancy.TenantId),
            StartDate: tenancy.StartDate,
            EndDate: tenancy.EndDate ?? "",
            MonthlyRent: String(tenancy.MonthlyRent),
            DepositAmount: String(tenancy.DepositAmount),
            PaymentDueDay: String(tenancy.PaymentDueDay),
            AgreementReference: tenancy.AgreementReference ?? "",
            Notes: tenancy.Notes ?? "",
          }),
        )
      : Promise.resolve();

    Promise.all([propertiesPromise, tenantsPromise, tenancyPromise])
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
    const request = isEdit ? updateTenancy(id, payload) : createTenancy(payload);
    request
      .then((tenancy) => {
        navigate(`/tenancies/${tenancy.TenancyId}`, {
          state: { toast: isEdit ? "Tenancy updated." : "Draft tenancy created." },
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
      <PageHeader
        title={isEdit ? "Edit tenancy" : "New tenancy"}
        description={!isEdit && "This creates a Draft. Activate it separately once you're ready to start the tenancy."}
      />

      {submitError && <ErrorMessage message={submitError} />}

      <form className="form-card" onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          <SelectField
            label="Property"
            name="PropertyId"
            value={form.PropertyId}
            onChange={updateField("PropertyId")}
            placeholder="Choose a property"
            options={propertyOptions}
            required
            error={errors.PropertyId}
          />
          <SelectField
            label="Tenant"
            name="TenantId"
            value={form.TenantId}
            onChange={updateField("TenantId")}
            placeholder="Choose a tenant"
            options={tenantOptions}
            required
            error={errors.TenantId}
          />
          <DateField
            label="Start date"
            name="StartDate"
            value={form.StartDate}
            onChange={updateField("StartDate")}
            required
            error={errors.StartDate}
          />
          <DateField
            label="End date"
            name="EndDate"
            value={form.EndDate}
            onChange={updateField("EndDate")}
            error={errors.EndDate}
          />
          <CurrencyField
            label="Monthly rent"
            name="MonthlyRent"
            value={form.MonthlyRent}
            onChange={updateField("MonthlyRent")}
            required
            error={errors.MonthlyRent}
          />
          <CurrencyField
            label="Deposit"
            name="DepositAmount"
            value={form.DepositAmount}
            onChange={updateField("DepositAmount")}
            error={errors.DepositAmount}
          />
          <FormField
            label="Payment due day"
            name="PaymentDueDay"
            type="number"
            value={form.PaymentDueDay}
            onChange={updateField("PaymentDueDay")}
            required
            error={errors.PaymentDueDay}
            placeholder="1-28"
          />
          <FormField
            label="Agreement reference"
            name="AgreementReference"
            value={form.AgreementReference}
            onChange={updateField("AgreementReference")}
          />
          <div className="form-field--full">
            <FormField label="Notes" name="Notes" value={form.Notes} onChange={updateField("Notes")} />
          </div>
        </div>

        <div className="form-card__actions">
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create draft tenancy"}
          </button>
          <button type="button" className="button button--secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
