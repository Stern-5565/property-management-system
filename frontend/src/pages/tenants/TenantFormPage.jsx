/**
 * Shared create/edit form - POST/PUT /api/tenants (see tenantService.js).
 * Same client/server validation split as LandlordFormPage.jsx: required
 * names, email shape, and date-of-birth-not-in-future (mirroring
 * TenantWriteBase.date_of_birth_not_in_future) are checked here for
 * instant feedback; anything else is left to the server's own message.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SelectField } from "../../components/SelectField";
import { DateField } from "../../components/DateField";
import { EMPLOYMENT_STATUS_OPTIONS } from "../../constants/tenantOptions";
import { getTenant, createTenant, updateTenant } from "../../services/tenantService";
import { getErrorMessage } from "../../utilities/apiError";

const BLANK_FORM = {
  FirstName: "",
  LastName: "",
  Email: "",
  Phone: "",
  DateOfBirth: "",
  PreviousAddress: "",
  EmergencyContactName: "",
  EmergencyContactPhone: "",
  IdentificationReference: "",
  EmploymentStatus: "",
  Notes: "",
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const TODAY = new Date().toISOString().slice(0, 10);

function validate(form) {
  const errors = {};
  if (!form.FirstName.trim()) errors.FirstName = "First name is required.";
  if (!form.LastName.trim()) errors.LastName = "Last name is required.";
  if (form.Email.trim() && !EMAIL_PATTERN.test(form.Email.trim())) {
    errors.Email = "Enter a valid email address.";
  }
  if (form.DateOfBirth && form.DateOfBirth > TODAY) {
    errors.DateOfBirth = "Date of birth cannot be in the future.";
  }
  return errors;
}

function toPayload(form) {
  const emptyToNull = (value) => (value.trim() === "" ? null : value.trim());
  return {
    FirstName: form.FirstName.trim(),
    LastName: form.LastName.trim(),
    Email: emptyToNull(form.Email),
    Phone: emptyToNull(form.Phone),
    DateOfBirth: form.DateOfBirth === "" ? null : form.DateOfBirth,
    PreviousAddress: emptyToNull(form.PreviousAddress),
    EmergencyContactName: emptyToNull(form.EmergencyContactName),
    EmergencyContactPhone: emptyToNull(form.EmergencyContactPhone),
    IdentificationReference: emptyToNull(form.IdentificationReference),
    EmploymentStatus: form.EmploymentStatus === "" ? null : form.EmploymentStatus,
    Notes: emptyToNull(form.Notes),
  };
}

export function TenantFormPage() {
  const { id } = useParams();
  const isEdit = id !== undefined;
  const navigate = useNavigate();

  const [form, setForm] = useState(BLANK_FORM);
  const [loading, setLoading] = useState(isEdit);
  const [loadError, setLoadError] = useState(null);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isEdit) {
      return;
    }
    getTenant(id)
      .then((tenant) =>
        setForm({
          FirstName: tenant.FirstName,
          LastName: tenant.LastName,
          Email: tenant.Email ?? "",
          Phone: tenant.Phone ?? "",
          DateOfBirth: tenant.DateOfBirth ?? "",
          PreviousAddress: tenant.PreviousAddress ?? "",
          EmergencyContactName: tenant.EmergencyContactName ?? "",
          EmergencyContactPhone: tenant.EmergencyContactPhone ?? "",
          IdentificationReference: tenant.IdentificationReference ?? "",
          EmploymentStatus: tenant.EmploymentStatus ?? "",
          Notes: tenant.Notes ?? "",
        }),
      )
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
    const request = isEdit ? updateTenant(id, payload) : createTenant(payload);
    request
      .then((tenant) => {
        navigate(`/tenants/${tenant.TenantId}`, {
          state: { toast: isEdit ? "Tenant updated." : "Tenant created." },
        });
      })
      .catch((err) => setSubmitError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  if (loading) {
    return <LoadingSpinner label="Loading tenant…" />;
  }

  if (loadError) {
    return <ErrorMessage message={loadError} />;
  }

  return (
    <div>
      <PageHeader title={isEdit ? "Edit tenant" : "New tenant"} />

      {submitError && <ErrorMessage message={submitError} />}

      <form className="form-card" onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          <FormField
            label="First name"
            name="FirstName"
            value={form.FirstName}
            onChange={updateField("FirstName")}
            required
            error={errors.FirstName}
          />
          <FormField
            label="Last name"
            name="LastName"
            value={form.LastName}
            onChange={updateField("LastName")}
            required
            error={errors.LastName}
          />
          <FormField
            label="Email"
            name="Email"
            type="email"
            value={form.Email}
            onChange={updateField("Email")}
            error={errors.Email}
          />
          <FormField label="Phone" name="Phone" value={form.Phone} onChange={updateField("Phone")} />
          <DateField
            label="Date of birth"
            name="DateOfBirth"
            value={form.DateOfBirth}
            onChange={updateField("DateOfBirth")}
            max={TODAY}
            error={errors.DateOfBirth}
          />
          <SelectField
            label="Employment status"
            name="EmploymentStatus"
            value={form.EmploymentStatus}
            onChange={updateField("EmploymentStatus")}
            placeholder="Not specified"
            options={EMPLOYMENT_STATUS_OPTIONS}
          />
          <div className="form-field--full">
            <FormField
              label="Previous address"
              name="PreviousAddress"
              value={form.PreviousAddress}
              onChange={updateField("PreviousAddress")}
            />
          </div>
          <FormField
            label="Identification reference"
            name="IdentificationReference"
            value={form.IdentificationReference}
            onChange={updateField("IdentificationReference")}
          />
          <FormField
            label="Emergency contact name"
            name="EmergencyContactName"
            value={form.EmergencyContactName}
            onChange={updateField("EmergencyContactName")}
          />
          <FormField
            label="Emergency contact phone"
            name="EmergencyContactPhone"
            value={form.EmergencyContactPhone}
            onChange={updateField("EmergencyContactPhone")}
          />
          <div className="form-field--full">
            <FormField label="Notes" name="Notes" value={form.Notes} onChange={updateField("Notes")} />
          </div>
        </div>

        <div className="form-card__actions">
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create tenant"}
          </button>
          <button type="button" className="button button--secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
