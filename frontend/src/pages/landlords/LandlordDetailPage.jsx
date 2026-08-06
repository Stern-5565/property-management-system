/**
 * GET /api/landlords/{id}, plus the deactivate/reactivate actions
 * (DELETE and PATCH /status respectively - see landlordService.js for
 * why they're two different endpoints). Stays on this page after either
 * action rather than navigating away, so the operator immediately sees
 * the result on the same record.
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
import { CAN_MANAGE_LANDLORDS } from "../../constants/roles";
import { getLandlord, setLandlordStatus, deactivateLandlord } from "../../services/landlordService";
import { getErrorMessage } from "../../utilities/apiError";

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

export function LandlordDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_LANDLORDS);
  const navigate = useNavigate();
  const location = useLocation();

  const [landlord, setLandlord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  // Same one-time-consume pattern as LandlordsListPage - a create/edit on
  // LandlordFormPage navigates here with { state: { toast } }; clear it
  // from history state so a refresh doesn't re-show it.
  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadLandlord = useCallback(() => {
    setLoading(true);
    setError(null);
    getLandlord(id)
      .then(setLandlord)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadLandlord();
  }, [loadLandlord]);

  function handleConfirmToggleStatus() {
    setActionSubmitting(true);
    setActionError(null);
    const action = landlord.IsActive ? deactivateLandlord(id) : setLandlordStatus(id, true);
    action
      .then(() => {
        setToast(landlord.IsActive ? "Landlord deactivated." : "Landlord reactivated.");
        loadLandlord();
      })
      .catch((err) => setActionError(getErrorMessage(err)))
      .finally(() => {
        // Close on both success and failure: a failure needs the dialog
        // closed too, otherwise the error message renders behind the
        // modal backdrop (z-index) and the user never actually sees it.
        setDialogOpen(false);
        setActionSubmitting(false);
      });
  }

  if (loading) {
    return <LoadingSpinner label="Loading landlord…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadLandlord} />;
  }

  return (
    <div>
      <PageHeader
        title={landlord.DisplayName}
        actions={
          canManage && (
            <Link to={`/landlords/${id}/edit`} className="button button--secondary">
              Edit
            </Link>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
      {actionError && <ErrorMessage message={actionError} />}

      <div className="detail-card">
        <StatusBadge status={landlord.IsActive ? "Active" : "Inactive"} />

        <div className="detail-grid">
          <Field label="Company" value={landlord.CompanyName} />
          <Field label="Contact name" value={[landlord.FirstName, landlord.LastName].filter(Boolean).join(" ") || null} />
          <Field label="Email" value={landlord.Email} />
          <Field label="Phone" value={landlord.Phone} />
          <Field label="Address" value={[landlord.AddressLine1, landlord.AddressLine2].filter(Boolean).join(", ")} />
          <Field label="City" value={landlord.City} />
          <Field label="Postcode" value={landlord.Postcode} />
          <Field label="Country" value={landlord.Country} />
          <Field label="Preferred contact method" value={landlord.PreferredContactMethod} />
        </div>

        {canManage && (
          <div className="detail-card__actions">
            <button
              type="button"
              className={landlord.IsActive ? "button button--danger" : "button"}
              onClick={() => setDialogOpen(true)}
            >
              {landlord.IsActive ? "Deactivate" : "Reactivate"}
            </button>
          </div>
        )}
      </div>

      <ConfirmationDialog
        open={dialogOpen}
        title={landlord.IsActive ? "Deactivate this landlord?" : "Reactivate this landlord?"}
        message={
          landlord.IsActive
            ? "This is blocked if they still have active properties - reassign or deactivate those first."
            : "They'll show as active again immediately."
        }
        confirmLabel={landlord.IsActive ? "Deactivate" : "Reactivate"}
        danger={landlord.IsActive}
        confirmDisabled={actionSubmitting}
        onCancel={() => setDialogOpen(false)}
        onConfirm={handleConfirmToggleStatus}
      />

      <p>
        <Link to="/landlords">← Back to landlords</Link>
      </p>
    </div>
  );
}
