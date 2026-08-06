/**
 * Shared create/edit form - POST /api/landlords when there's no :id in
 * the route, PUT /api/landlords/{id} when there is (see
 * services/landlordService.js). Client-side validation here only covers
 * what's cheap and obviously wrong (required fields, email shape, the
 * company-or-full-name rule) so a user gets instant feedback without a
 * round trip; anything the backend alone can determine (duplicate email)
 * is still shown via the server's own error message - the backend stays
 * the final authority, this is just a head start on the common cases.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SelectField } from "../../components/SelectField";
import { getLandlord, createLandlord, updateLandlord } from "../../services/landlordService";
import { getErrorMessage } from "../../utilities/apiError";

const BLANK_FORM = {
  FirstName: "",
  LastName: "",
  CompanyName: "",
  Email: "",
  Phone: "",
  AddressLine1: "",
  AddressLine2: "",
  City: "",
  Postcode: "",
  Country: "",
  PreferredContactMethod: "",
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate(form) {
  const errors = {};
  if (!form.AddressLine1.trim()) errors.AddressLine1 = "Address line 1 is required.";
  if (!form.City.trim()) errors.City = "City is required.";
  if (!form.Postcode.trim()) errors.Postcode = "Postcode is required.";
  if (!form.Country.trim()) errors.Country = "Country is required.";
  if (form.Email.trim() && !EMAIL_PATTERN.test(form.Email.trim())) {
    errors.Email = "Enter a valid email address.";
  }

  const hasCompany = form.CompanyName.trim().length > 0;
  const hasFullName = form.FirstName.trim().length > 0 && form.LastName.trim().length > 0;
  if (!hasCompany && !hasFullName) {
    errors._form = "Enter either a company name, or both a first and last name.";
  }
  return errors;
}

/** Optional text fields go to the API as null, not "" - matches what the
 * backend's Pydantic schema expects for "not provided". */
function toPayload(form) {
  const emptyToNull = (value) => (value.trim() === "" ? null : value.trim());
  return {
    FirstName: emptyToNull(form.FirstName),
    LastName: emptyToNull(form.LastName),
    CompanyName: emptyToNull(form.CompanyName),
    Email: emptyToNull(form.Email),
    Phone: emptyToNull(form.Phone),
    AddressLine1: form.AddressLine1.trim(),
    AddressLine2: emptyToNull(form.AddressLine2),
    City: form.City.trim(),
    Postcode: form.Postcode.trim(),
    Country: form.Country.trim(),
    PreferredContactMethod: form.PreferredContactMethod === "" ? null : form.PreferredContactMethod,
  };
}

export function LandlordFormPage() {
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
    getLandlord(id)
      .then((landlord) =>
        setForm({
          FirstName: landlord.FirstName ?? "",
          LastName: landlord.LastName ?? "",
          CompanyName: landlord.CompanyName ?? "",
          Email: landlord.Email ?? "",
          Phone: landlord.Phone ?? "",
          AddressLine1: landlord.AddressLine1,
          AddressLine2: landlord.AddressLine2 ?? "",
          City: landlord.City,
          Postcode: landlord.Postcode,
          Country: landlord.Country,
          PreferredContactMethod: landlord.PreferredContactMethod ?? "",
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
    const request = isEdit ? updateLandlord(id, payload) : createLandlord(payload);
    request
      .then((landlord) => {
        navigate(`/landlords/${landlord.LandlordId}`, {
          state: { toast: isEdit ? "Landlord updated." : "Landlord created." },
        });
      })
      .catch((err) => setSubmitError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  if (loading) {
    return <LoadingSpinner label="Loading landlord…" />;
  }

  if (loadError) {
    return <ErrorMessage message={loadError} />;
  }

  return (
    <div>
      <PageHeader title={isEdit ? "Edit landlord" : "New landlord"} />

      {errors._form && <ErrorMessage message={errors._form} />}
      {submitError && <ErrorMessage message={submitError} />}

      <form className="form-card" onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          <FormField label="First name" name="FirstName" value={form.FirstName} onChange={updateField("FirstName")} />
          <FormField label="Last name" name="LastName" value={form.LastName} onChange={updateField("LastName")} />
          <div className="form-field--full">
            <FormField
              label="Company name"
              name="CompanyName"
              value={form.CompanyName}
              onChange={updateField("CompanyName")}
            />
          </div>
          <FormField
            label="Email"
            name="Email"
            type="email"
            value={form.Email}
            onChange={updateField("Email")}
            error={errors.Email}
          />
          <FormField label="Phone" name="Phone" value={form.Phone} onChange={updateField("Phone")} />
          <SelectField
            label="Preferred contact method"
            name="PreferredContactMethod"
            value={form.PreferredContactMethod}
            onChange={updateField("PreferredContactMethod")}
            placeholder="No preference"
            options={[
              { value: "Email", label: "Email" },
              { value: "Phone", label: "Phone" },
              { value: "Post", label: "Post" },
            ]}
          />
          <div className="form-field--full">
            <FormField
              label="Address line 1"
              name="AddressLine1"
              value={form.AddressLine1}
              onChange={updateField("AddressLine1")}
              required
              error={errors.AddressLine1}
            />
          </div>
          <div className="form-field--full">
            <FormField
              label="Address line 2"
              name="AddressLine2"
              value={form.AddressLine2}
              onChange={updateField("AddressLine2")}
            />
          </div>
          <FormField
            label="City"
            name="City"
            value={form.City}
            onChange={updateField("City")}
            required
            error={errors.City}
          />
          <FormField
            label="Postcode"
            name="Postcode"
            value={form.Postcode}
            onChange={updateField("Postcode")}
            required
            error={errors.Postcode}
          />
          <FormField
            label="Country"
            name="Country"
            value={form.Country}
            onChange={updateField("Country")}
            required
            error={errors.Country}
          />
        </div>

        <div className="form-card__actions">
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create landlord"}
          </button>
          <button type="button" className="button button--secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
