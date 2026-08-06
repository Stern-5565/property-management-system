/**
 * GET /api/tenants/{id}, plus deactivate/reactivate - same shape as
 * LandlordDetailPage.jsx (Tenant's PATCH /status accepts IsActive either
 * direction, like Landlords, unlike Properties - see
 * tenantService.js).
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
import { CAN_MANAGE_TENANTS } from "../../constants/roles";
import { getTenant, setTenantStatus, deactivateTenant } from "../../services/tenantService";
import { getErrorMessage } from "../../utilities/apiError";

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

export function TenantDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_TENANTS);
  const navigate = useNavigate();
  const location = useLocation();

  const [tenant, setTenant] = useState(null);
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

  const loadTenant = useCallback(() => {
    setLoading(true);
    setError(null);
    getTenant(id)
      .then(setTenant)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadTenant();
  }, [loadTenant]);

  function handleConfirmToggleStatus() {
    setActionSubmitting(true);
    setActionError(null);
    const action = tenant.IsActive ? deactivateTenant(id) : setTenantStatus(id, true);
    action
      .then(() => {
        setToast(tenant.IsActive ? "Tenant deactivated." : "Tenant reactivated.");
        loadTenant();
      })
      .catch((err) => setActionError(getErrorMessage(err)))
      .finally(() => {
        setDialogOpen(false);
        setActionSubmitting(false);
      });
  }

  if (loading) {
    return <LoadingSpinner label="Loading tenant…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadTenant} />;
  }

  return (
    <div>
      <PageHeader
        title={`${tenant.FirstName} ${tenant.LastName}`}
        actions={
          canManage && (
            <Link to={`/tenants/${id}/edit`} className="button button--secondary">
              Edit
            </Link>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
      {actionError && <ErrorMessage message={actionError} />}

      <div className="detail-card">
        <StatusBadge status={tenant.IsActive ? "Active" : "Inactive"} />

        <div className="detail-grid">
          <Field label="Email" value={tenant.Email} />
          <Field label="Phone" value={tenant.Phone} />
          <Field label="Date of birth" value={tenant.DateOfBirth} />
          <Field label="Employment status" value={tenant.EmploymentStatus} />
          <Field label="Previous address" value={tenant.PreviousAddress} />
          <Field label="Identification reference" value={tenant.IdentificationReference} />
          <Field label="Emergency contact" value={tenant.EmergencyContactName} />
          <Field label="Emergency contact phone" value={tenant.EmergencyContactPhone} />
          <Field label="Notes" value={tenant.Notes} />
        </div>

        {canManage && (
          <div className="detail-card__actions">
            <button
              type="button"
              className={tenant.IsActive ? "button button--danger" : "button"}
              onClick={() => setDialogOpen(true)}
            >
              {tenant.IsActive ? "Deactivate" : "Reactivate"}
            </button>
          </div>
        )}
      </div>

      <ConfirmationDialog
        open={dialogOpen}
        title={tenant.IsActive ? "Deactivate this tenant?" : "Reactivate this tenant?"}
        message={
          tenant.IsActive
            ? "This is blocked if they still have an active, upcoming, or draft tenancy - end or cancel that first."
            : "They'll show as active again immediately."
        }
        confirmLabel={tenant.IsActive ? "Deactivate" : "Reactivate"}
        danger={tenant.IsActive}
        confirmDisabled={actionSubmitting}
        onCancel={() => setDialogOpen(false)}
        onConfirm={handleConfirmToggleStatus}
      />

      <p>
        <Link to="/tenants">← Back to tenants</Link>
      </p>
    </div>
  );
}
