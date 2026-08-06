/**
 * GET /api/properties/{id}, plus the linked landlord's display name (a
 * second small GET /api/landlords/{id} - PropertyResponse only carries
 * LandlordId, not a name, so this is the one extra call needed to show
 * something more useful than a bare number).
 *
 * Status vs. active/inactive are two SEPARATE actions here, unlike
 * Landlords: "Change status" (PropertyStatus - Vacant/Occupied/...) is
 * freely reversible, so it's a direct action with no confirmation
 * dialog. "Deactivate" (IsActive) is the one-way, confirmed action - and
 * there is no "Reactivate" counterpart, because the backend has no
 * endpoint for it (see propertyService.js's module docstring). That's a
 * real gap in the current API, not an oversight here.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { SelectField } from "../../components/SelectField";
import { ConfirmationDialog } from "../../components/ConfirmationDialog";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_PROPERTIES } from "../../constants/roles";
import { PROPERTY_STATUS_OPTIONS } from "../../constants/propertyOptions";
import { getProperty, setPropertyStatus, deactivateProperty } from "../../services/propertyService";
import { getLandlord } from "../../services/landlordService";
import { getErrorMessage } from "../../utilities/apiError";

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

export function PropertyDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_PROPERTIES);
  const navigate = useNavigate();
  const location = useLocation();

  const [property, setProperty] = useState(null);
  const [landlord, setLandlord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusChoice, setStatusChoice] = useState("");
  const [statusSubmitting, setStatusSubmitting] = useState(false);
  const [statusError, setStatusError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deactivateSubmitting, setDeactivateSubmitting] = useState(false);
  const [deactivateError, setDeactivateError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadProperty = useCallback(() => {
    setLoading(true);
    setError(null);
    getProperty(id)
      .then((data) => {
        setProperty(data);
        setStatusChoice(data.PropertyStatus);
        return getLandlord(data.LandlordId).catch(() => null); // landlord name is a nice-to-have, not load-blocking
      })
      .then(setLandlord)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadProperty();
  }, [loadProperty]);

  function handleUpdateStatus() {
    setStatusSubmitting(true);
    setStatusError(null);
    setPropertyStatus(id, statusChoice)
      .then((updated) => {
        setProperty(updated);
        setToast("Status updated.");
      })
      .catch((err) => setStatusError(getErrorMessage(err)))
      .finally(() => setStatusSubmitting(false));
  }

  function handleConfirmDeactivate() {
    setDeactivateSubmitting(true);
    setDeactivateError(null);
    deactivateProperty(id)
      .then(() => {
        setToast("Property deactivated.");
        loadProperty();
      })
      .catch((err) => setDeactivateError(getErrorMessage(err)))
      .finally(() => {
        setDialogOpen(false);
        setDeactivateSubmitting(false);
      });
  }

  if (loading) {
    return <LoadingSpinner label="Loading property…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadProperty} />;
  }

  return (
    <div>
      <PageHeader
        title={property.PropertyReference}
        actions={
          canManage && (
            <Link to={`/properties/${id}/edit`} className="button button--secondary">
              Edit
            </Link>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="detail-card">
        <StatusBadge status={property.PropertyStatus} />

        <div className="detail-grid">
          <Field label="Landlord" value={landlord ? <Link to={`/landlords/${landlord.LandlordId}`}>{landlord.DisplayName}</Link> : "—"} />
          <Field label="Active" value={property.IsActive ? "Yes" : "No"} />
          <Field label="Address" value={[property.AddressLine1, property.AddressLine2].filter(Boolean).join(", ")} />
          <Field label="City" value={property.City} />
          <Field label="Postcode" value={property.Postcode} />
          <Field label="Country" value={property.Country} />
          <Field label="Type" value={property.PropertyType} />
          <Field label="Bedrooms" value={property.Bedrooms} />
          <Field label="Bathrooms" value={property.Bathrooms} />
          <Field label="Monthly rent" value={`£${property.MonthlyRent}`} />
          <Field label="Deposit" value={`£${property.DepositAmount}`} />
          <Field label="Date acquired" value={property.DateAcquired} />
          <Field label="Notes" value={property.Notes} />
        </div>

        {canManage && property.IsActive && (
          <>
            <div className="detail-card__actions">
              <SelectField
                label="Change status"
                name="statusChoice"
                value={statusChoice}
                onChange={(event) => setStatusChoice(event.target.value)}
                options={PROPERTY_STATUS_OPTIONS}
              />
              <button
                type="button"
                className="button button--secondary"
                onClick={handleUpdateStatus}
                disabled={statusSubmitting || statusChoice === property.PropertyStatus}
              >
                {statusSubmitting ? "Updating…" : "Update status"}
              </button>
            </div>
            {statusError && <ErrorMessage message={statusError} />}

            <div className="detail-card__actions">
              <button type="button" className="button button--danger" onClick={() => setDialogOpen(true)}>
                Deactivate
              </button>
            </div>
            {deactivateError && <ErrorMessage message={deactivateError} />}
          </>
        )}

        {!property.IsActive && <p>This property has been deactivated.</p>}
      </div>

      <ConfirmationDialog
        open={dialogOpen}
        title="Deactivate this property?"
        message="This is blocked if it still has an active, upcoming, or draft tenancy - end or cancel that first. This cannot currently be undone from the app."
        confirmLabel="Deactivate"
        danger
        confirmDisabled={deactivateSubmitting}
        onCancel={() => setDialogOpen(false)}
        onConfirm={handleConfirmDeactivate}
      />

      <p>
        <Link to="/properties">← Back to properties</Link>
      </p>
    </div>
  );
}
