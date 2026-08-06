/**
 * Shared create/edit form - POST/PUT /api/employees (see
 * employeeService.js). Unlike Landlord/Tenant, Email and HireDate are
 * both required here (EmployeeWriteBase has no optional-email escape
 * hatch - see backend/app/schemas/employee.py). Client-side validation
 * mirrors EmployeeWriteBase.hire_date_not_in_future (a DateField with
 * max={TODAY} plus an explicit check), same reasoning as
 * TenantFormPage's date-of-birth check; duplicate-email detection is left
 * to the server's own message, same as every other module's form.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { DateField } from "../../components/DateField";
import { getEmployee, createEmployee, updateEmployee } from "../../services/employeeService";
import { getErrorMessage } from "../../utilities/apiError";

const BLANK_FORM = {
  FirstName: "",
  LastName: "",
  Email: "",
  Phone: "",
  JobTitle: "",
  Department: "",
  HireDate: "",
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const TODAY = new Date().toISOString().slice(0, 10);

function validate(form) {
  const errors = {};
  if (!form.FirstName.trim()) errors.FirstName = "First name is required.";
  if (!form.LastName.trim()) errors.LastName = "Last name is required.";
  if (!form.Email.trim()) {
    errors.Email = "Email is required.";
  } else if (!EMAIL_PATTERN.test(form.Email.trim())) {
    errors.Email = "Enter a valid email address.";
  }
  if (!form.HireDate) {
    errors.HireDate = "Hire date is required.";
  } else if (form.HireDate > TODAY) {
    errors.HireDate = "Hire date cannot be in the future.";
  }
  return errors;
}

function toPayload(form) {
  const emptyToNull = (value) => (value.trim() === "" ? null : value.trim());
  return {
    FirstName: form.FirstName.trim(),
    LastName: form.LastName.trim(),
    Email: form.Email.trim(),
    Phone: emptyToNull(form.Phone),
    JobTitle: emptyToNull(form.JobTitle),
    Department: emptyToNull(form.Department),
    HireDate: form.HireDate,
  };
}

export function EmployeeFormPage() {
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
    getEmployee(id)
      .then((employee) =>
        setForm({
          FirstName: employee.FirstName,
          LastName: employee.LastName,
          Email: employee.Email,
          Phone: employee.Phone ?? "",
          JobTitle: employee.JobTitle ?? "",
          Department: employee.Department ?? "",
          HireDate: employee.HireDate,
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
    const request = isEdit ? updateEmployee(id, payload) : createEmployee(payload);
    request
      .then((employee) => {
        navigate(`/employees/${employee.EmployeeId}`, {
          state: { toast: isEdit ? "Employee updated." : "Employee created." },
        });
      })
      .catch((err) => setSubmitError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  if (loading) {
    return <LoadingSpinner label="Loading employee…" />;
  }

  if (loadError) {
    return <ErrorMessage message={loadError} />;
  }

  return (
    <div>
      <PageHeader title={isEdit ? "Edit employee" : "New employee"} />

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
            required
            error={errors.Email}
          />
          <FormField label="Phone" name="Phone" value={form.Phone} onChange={updateField("Phone")} />
          <FormField label="Job title" name="JobTitle" value={form.JobTitle} onChange={updateField("JobTitle")} />
          <FormField label="Department" name="Department" value={form.Department} onChange={updateField("Department")} />
          <DateField
            label="Hire date"
            name="HireDate"
            value={form.HireDate}
            onChange={updateField("HireDate")}
            max={TODAY}
            required
            error={errors.HireDate}
          />
        </div>

        <div className="form-card__actions">
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create employee"}
          </button>
          <button type="button" className="button button--secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
