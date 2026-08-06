/**
 * Shared create/edit form - POST/PUT /api/maintenance-requests. PUT is
 * rejected once the request is Completed/Cancelled
 * (MAINTENANCE_REQUEST_CLOSED, 409), which is why
 * MaintenanceRequestDetailPage only shows the Edit link while the
 * request is still open. Property/Tenancy/Tenant selectors load the same
 * direct pageSize:100 way every other module's dropdowns do -
 * Tenancy/Tenant are optional here (a request can be raised against a
 * property with no specific tenancy/tenant tied to it, e.g. a communal
 * area issue).
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SelectField } from "../../components/SelectField";
import { DateField } from "../../components/DateField";
import { CATEGORY_OPTIONS, PRIORITY_OPTIONS } from "../../constants/maintenanceOptions";
import { getRequest, createRequest, updateRequest } from "../../services/maintenanceService";
import { listProperties } from "../../services/propertyService";
import { listTenancies } from "../../services/tenancyService";
import { listTenants } from "../../services/tenantService";
import { getErrorMessage } from "../../utilities/apiError";

const BLANK_FORM = {
  PropertyId: "",
  TenancyId: "",
  TenantId: "",
  RequestReference: "",
  Title: "",
  Description: "",
  Category: "",
  Priority: "",
  ScheduledDate: "",
};

function validate(form) {
  const errors = {};
  if (!form.PropertyId) errors.PropertyId = "Choose a property.";
  if (!form.RequestReference.trim()) errors.RequestReference = "Request reference is required.";
  if (!form.Title.trim()) errors.Title = "Title is required.";
  if (!form.Category) errors.Category = "Choose a category.";
  if (!form.Priority) errors.Priority = "Choose a priority.";
  return errors;
}

function toPayload(form) {
  const emptyToNull = (value) => (value.trim() === "" ? null : value.trim());
  return {
    PropertyId: Number(form.PropertyId),
    TenancyId: form.TenancyId === "" ? null : Number(form.TenancyId),
    TenantId: form.TenantId === "" ? null : Number(form.TenantId),
    RequestReference: form.RequestReference.trim(),
    Title: form.Title.trim(),
    Description: emptyToNull(form.Description),
    Category: form.Category,
    Priority: form.Priority,
    ScheduledDate: form.ScheduledDate === "" ? null : form.ScheduledDate,
  };
}

export function MaintenanceRequestFormPage() {
  const { id } = useParams();
  const isEdit = id !== undefined;
  const navigate = useNavigate();

  const [form, setForm] = useState(BLANK_FORM);
  const [propertyOptions, setPropertyOptions] = useState([]);
  const [tenancyOptions, setTenancyOptions] = useState([]);
  const [tenantOptions, setTenantOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const propertiesPromise = listProperties({ pageSize: 100 }).then((data) =>
      setPropertyOptions(data.items.map((p) => ({ value: String(p.PropertyId), label: p.PropertyReference }))),
    );
    const tenanciesPromise = listTenancies({ pageSize: 100 }).then((data) =>
      setTenancyOptions(
        data.items.map((t) => ({ value: String(t.TenancyId), label: `${t.PropertyReference} — ${t.TenantName}` })),
      ),
    );
    const tenantsPromise = listTenants({ pageSize: 100 }).then((data) =>
      setTenantOptions(data.items.map((t) => ({ value: String(t.TenantId), label: `${t.FirstName} ${t.LastName}` }))),
    );
    const requestPromise = isEdit
      ? getRequest(id).then((request) =>
          setForm({
            PropertyId: String(request.PropertyId),
            TenancyId: request.TenancyId ? String(request.TenancyId) : "",
            TenantId: request.TenantId ? String(request.TenantId) : "",
            RequestReference: request.RequestReference,
            Title: request.Title,
            Description: request.Description ?? "",
            Category: request.Category,
            Priority: request.Priority,
            ScheduledDate: request.ScheduledDate ?? "",
          }),
        )
      : Promise.resolve();

    Promise.all([propertiesPromise, tenanciesPromise, tenantsPromise, requestPromise])
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
    const request = isEdit ? updateRequest(id, payload) : createRequest(payload);
    request
      .then((data) => {
        navigate(`/maintenance/${data.MaintenanceRequestId}`, {
          state: { toast: isEdit ? "Request updated." : "Maintenance request created." },
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
      <PageHeader title={isEdit ? "Edit maintenance request" : "New maintenance request"} />

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
          <div className="form-field--full">
            <FormField
              label="Title"
              name="Title"
              value={form.Title}
              onChange={updateField("Title")}
              required
              error={errors.Title}
            />
          </div>
          <SelectField
            label="Tenancy (optional)"
            name="TenancyId"
            value={form.TenancyId}
            onChange={updateField("TenancyId")}
            placeholder="No specific tenancy"
            options={tenancyOptions}
          />
          <SelectField
            label="Tenant (optional)"
            name="TenantId"
            value={form.TenantId}
            onChange={updateField("TenantId")}
            placeholder="No specific tenant"
            options={tenantOptions}
          />
          <FormField
            label="Request reference"
            name="RequestReference"
            value={form.RequestReference}
            onChange={updateField("RequestReference")}
            required
            error={errors.RequestReference}
          />
          <SelectField
            label="Category"
            name="Category"
            value={form.Category}
            onChange={updateField("Category")}
            placeholder="Choose a category"
            options={CATEGORY_OPTIONS}
            required
            error={errors.Category}
          />
          <SelectField
            label="Priority"
            name="Priority"
            value={form.Priority}
            onChange={updateField("Priority")}
            placeholder="Choose a priority"
            options={PRIORITY_OPTIONS}
            required
            error={errors.Priority}
          />
          <DateField
            label="Scheduled date (optional)"
            name="ScheduledDate"
            value={form.ScheduledDate}
            onChange={updateField("ScheduledDate")}
          />
          <div className="form-field--full">
            <FormField
              label="Description"
              name="Description"
              value={form.Description}
              onChange={updateField("Description")}
            />
          </div>
        </div>

        <div className="form-card__actions">
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create request"}
          </button>
          <button type="button" className="button button--secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
