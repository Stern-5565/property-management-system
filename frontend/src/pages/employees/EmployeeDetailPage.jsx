/**
 * GET /api/employees/{id}, plus deactivate/reactivate - same shape as
 * TenantDetailPage.jsx (Employee's PATCH /status also accepts IsActive
 * either direction). Actions gate on CAN_MANAGE_EMPLOYEES
 * (Administrator-only - see roles.js).
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { ConfirmationDialog } from "../../components/ConfirmationDialog";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_EMPLOYEES } from "../../constants/roles";
import { getEmployee, setEmployeeStatus, deactivateEmployee } from "../../services/employeeService";
import { getErrorMessage } from "../../utilities/apiError";

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

export function EmployeeDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_EMPLOYEES);
  const navigate = useNavigate();
  const location = useLocation();

  const [employee, setEmployee] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadEmployee = useCallback(() => {
    setLoading(true);
    setError(null);
    getEmployee(id)
      .then(setEmployee)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadEmployee();
  }, [loadEmployee]);

  function handleConfirmToggleStatus() {
    setActionSubmitting(true);
    setActionError(null);
    const action = employee.IsActive ? deactivateEmployee(id) : setEmployeeStatus(id, true);
    action
      .then(() => {
        setToast(employee.IsActive ? "Employee deactivated." : "Employee reactivated.");
        loadEmployee();
      })
      .catch((err) => setActionError(getErrorMessage(err)))
      .finally(() => {
        setDialogOpen(false);
        setActionSubmitting(false);
      });
  }

  if (loading) {
    return <LoadingSpinner label="Loading employee…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadEmployee} />;
  }

  return (
    <div>
      <PageHeader
        title={`${employee.FirstName} ${employee.LastName}`}
        actions={
          canManage && (
            <Link to={`/employees/${id}/edit`} className="button button--secondary">
              Edit
            </Link>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
      {actionError && <ErrorMessage message={actionError} />}

      <div className="detail-card">
        <StatusBadge status={employee.IsActive ? "Active" : "Inactive"} />

        <div className="detail-grid">
          <Field label="Email" value={employee.Email} />
          <Field label="Phone" value={employee.Phone} />
          <Field label="Job title" value={employee.JobTitle} />
          <Field label="Department" value={employee.Department} />
          <Field label="Hire date" value={employee.HireDate} />
        </div>

        {canManage && (
          <div className="detail-card__actions">
            <button
              type="button"
              className={employee.IsActive ? "button button--danger" : "button"}
              onClick={() => setDialogOpen(true)}
            >
              {employee.IsActive ? "Deactivate" : "Reactivate"}
            </button>
          </div>
        )}
      </div>

      <ConfirmationDialog
        open={dialogOpen}
        title={employee.IsActive ? "Deactivate this employee?" : "Reactivate this employee?"}
        message={
          employee.IsActive
            ? "This is blocked if they still have open maintenance requests assigned to them - reassign those first. It also disables their login access, if they have a user account (this does not restore automatically on reactivation)."
            : "They'll show as active again immediately. Note this does not restore their login access if it was disabled - that's a separate, Administrator-only user account action."
        }
        confirmLabel={employee.IsActive ? "Deactivate" : "Reactivate"}
        danger={employee.IsActive}
        confirmDisabled={actionSubmitting}
        onCancel={() => setDialogOpen(false)}
        onConfirm={handleConfirmToggleStatus}
      />

      <p>
        <Link to="/employees">← Back to employees</Link>
      </p>
    </div>
  );
}
