/**
 * Shared create/edit form - POST/PUT /api/properties (see
 * propertyService.js). Same client/server validation split as
 * LandlordFormPage.jsx: required fields and simple numeric bounds are
 * checked here for instant feedback; duplicate-reference and
 * unknown-landlord errors are left entirely to the server's message.
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
import { PROPERTY_TYPE_OPTIONS } from "../../constants/propertyOptions";
import { getProperty, createProperty, updateProperty } from "../../services/propertyService";
import { listLandlords } from "../../services/landlordService";
import { getErrorMessage } from "../../utilities/apiError";

const BLANK_FORM = {
  LandlordId: "",
  PropertyReference: "",
  AddressLine1: "",
  AddressLine2: "",
  City: "",
  Postcode: "",
  Country: "",
  PropertyType: "",
  Bedrooms: "",
  Bathrooms: "",
  MonthlyRent: "",
  DepositAmount: "0",
  DateAcquired: "",
  Notes: "",
};

function validate(form) {
  const errors = {};
  if (!form.LandlordId) errors.LandlordId = "Choose a landlord.";
  if (!form.PropertyReference.trim()) errors.PropertyReference = "Property reference is required.";
  if (!form.AddressLine1.trim()) errors.AddressLine1 = "Address line 1 is required.";
  if (!form.City.trim()) errors.City = "City is required.";
  if (!form.Postcode.trim()) errors.Postcode = "Postcode is required.";
  if (!form.Country.trim()) errors.Country = "Country is required.";
  if (!form.PropertyType) errors.PropertyType = "Choose a property type.";

  if (form.Bedrooms === "" || Number(form.Bedrooms) < 0 || !Number.isInteger(Number(form.Bedrooms))) {
    errors.Bedrooms = "Enter a whole number of 0 or more.";
  }
  if (form.Bathrooms === "" || Number(form.Bathrooms) < 0 || !Number.isInteger(Number(form.Bathrooms))) {
    errors.Bathrooms = "Enter a whole number of 0 or more.";
  }
  if (form.MonthlyRent === "" || Number(form.MonthlyRent) < 0) {
    errors.MonthlyRent = "Enter a monthly rent of 0 or more.";
  }
  if (form.DepositAmount !== "" && Number(form.DepositAmount) < 0) {
    errors.DepositAmount = "Deposit cannot be negative.";
  }
  return errors;
}

function toPayload(form) {
  const emptyToNull = (value) => (value.trim() === "" ? null : value.trim());
  return {
    LandlordId: Number(form.LandlordId),
    PropertyReference: form.PropertyReference.trim(),
    AddressLine1: form.AddressLine1.trim(),
    AddressLine2: emptyToNull(form.AddressLine2),
    City: form.City.trim(),
    Postcode: form.Postcode.trim(),
    Country: form.Country.trim(),
    PropertyType: form.PropertyType,
    Bedrooms: Number(form.Bedrooms),
    Bathrooms: Number(form.Bathrooms),
    MonthlyRent: form.MonthlyRent.trim(),
    DepositAmount: form.DepositAmount.trim() === "" ? "0.00" : form.DepositAmount.trim(),
    DateAcquired: emptyToNull(form.DateAcquired),
    Notes: emptyToNull(form.Notes),
  };
}

export function PropertyFormPage() {
  const { id } = useParams();
  const isEdit = id !== undefined;
  const navigate = useNavigate();

  const [form, setForm] = useState(BLANK_FORM);
  const [landlordOptions, setLandlordOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const landlordsPromise = listLandlords({ pageSize: 100, isActive: true }).then((data) =>
      setLandlordOptions(data.items.map((l) => ({ value: String(l.LandlordId), label: l.DisplayName }))),
    );
    const propertyPromise = isEdit
      ? getProperty(id).then((property) =>
          setForm({
            LandlordId: String(property.LandlordId),
            PropertyReference: property.PropertyReference,
            AddressLine1: property.AddressLine1,
            AddressLine2: property.AddressLine2 ?? "",
            City: property.City,
            Postcode: property.Postcode,
            Country: property.Country,
            PropertyType: property.PropertyType,
            Bedrooms: String(property.Bedrooms),
            Bathrooms: String(property.Bathrooms),
            MonthlyRent: String(property.MonthlyRent),
            DepositAmount: String(property.DepositAmount),
            DateAcquired: property.DateAcquired ?? "",
            Notes: property.Notes ?? "",
          }),
        )
      : Promise.resolve();

    Promise.all([landlordsPromise, propertyPromise])
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
    const request = isEdit ? updateProperty(id, payload) : createProperty(payload);
    request
      .then((property) => {
        navigate(`/properties/${property.PropertyId}`, {
          state: { toast: isEdit ? "Property updated." : "Property created." },
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
      <PageHeader title={isEdit ? "Edit property" : "New property"} />

      {submitError && <ErrorMessage message={submitError} />}

      <form className="form-card" onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          <div className="form-field--full">
            <SelectField
              label="Landlord"
              name="LandlordId"
              value={form.LandlordId}
              onChange={updateField("LandlordId")}
              placeholder="Choose a landlord"
              options={landlordOptions}
              required
              error={errors.LandlordId}
            />
          </div>
          <FormField
            label="Property reference"
            name="PropertyReference"
            value={form.PropertyReference}
            onChange={updateField("PropertyReference")}
            required
            error={errors.PropertyReference}
          />
          <SelectField
            label="Property type"
            name="PropertyType"
            value={form.PropertyType}
            onChange={updateField("PropertyType")}
            placeholder="Choose a type"
            options={PROPERTY_TYPE_OPTIONS}
            required
            error={errors.PropertyType}
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
          <FormField
            label="Bedrooms"
            name="Bedrooms"
            type="number"
            value={form.Bedrooms}
            onChange={updateField("Bedrooms")}
            required
            error={errors.Bedrooms}
          />
          <FormField
            label="Bathrooms"
            name="Bathrooms"
            type="number"
            value={form.Bathrooms}
            onChange={updateField("Bathrooms")}
            required
            error={errors.Bathrooms}
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
          <DateField label="Date acquired" name="DateAcquired" value={form.DateAcquired} onChange={updateField("DateAcquired")} />
          <div className="form-field--full">
            <FormField label="Notes" name="Notes" value={form.Notes} onChange={updateField("Notes")} />
          </div>
        </div>

        <div className="form-card__actions">
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create property"}
          </button>
          <button type="button" className="button button--secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
