/**
 * GET /api/tenancies/{id}, plus the three lifecycle actions (activate/
 * end/cancel). Unlike every earlier module, there's no single "toggle
 * status" action - which actions are even available depends on the
 * tenancy's CURRENT TenancyStatus, mirroring tenancy_service.py exactly:
 *   - Edit link and "Activate" only show for Draft.
 *   - "End tenancy" only shows for Active/Ending Soon.
 *   - "Cancel tenancy" shows for anything not already Ended/Cancelled.
 * All three share one ConfirmationDialog (only one action is ever mid-
 * flight at a time) rather than three separate dialog instances - see
 * `pendingAction` below and DIALOG_CONFIG for the per-action copy.
 *
 * Error messages are shown verbatim from the backend (e.g.
 * TENANCY_DATE_CONFLICT, PROPERTY_INACTIVE, TENANT_INACTIVE) rather than
 * re-validated client-side - the scope doc's Prompt 21 explicitly says
 * not to duplicate backend business-rule validation here.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { DateField } from "../../components/DateField";
import { ConfirmationDialog } from "../../components/ConfirmationDialog";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_TENANCIES } from "../../constants/roles";
import { getTenancy, activateTenancy, endTenancy, cancelTenancy } from "../../services/tenancyService";
import { getErrorMessage } from "../../utilities/apiError";

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

export function TenancyDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_TENANCIES);
  const navigate = useNavigate();
  const location = useLocation();

  const [tenancy, setTenancy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [endDateChoice, setEndDateChoice] = useState("");
  const [pendingAction, setPendingAction] = useState(null); // "activate" | "end" | "cancel" | null
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadTenancy = useCallback(() => {
    setLoading(true);
    setError(null);
    getTenancy(id)
      .then(setTenancy)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadTenancy();
  }, [loadTenancy]);

  const dialogConfig = useMemo(
    () => ({
      activate: {
        title: "Activate this tenancy?",
        message:
          "This assigns the tenant to the property (marking it Occupied once the start date arrives) and checks for date conflicts. Blocked if the property or tenant is inactive, or if another tenancy already covers these dates on this property.",
        confirmLabel: "Activate",
        cancelLabel: "Cancel",
        danger: false,
      },
      end: {
        title: "End this tenancy?",
        message: endDateChoice
          ? `Ends the tenancy on ${endDateChoice}. The property will be marked Vacant unless another tenancy is already lined up.`
          : "Ends the tenancy today, since no end date was chosen. The property will be marked Vacant unless another tenancy is already lined up.",
        confirmLabel: "End tenancy",
        cancelLabel: "Cancel",
        danger: true,
      },
      cancel: {
        title: "Cancel this tenancy?",
        message:
          "This cannot be undone. If the tenancy was Active, the property will be marked Vacant unless another tenancy is already lined up.",
        confirmLabel: "Cancel tenancy",
        cancelLabel: "Go back",
        danger: true,
      },
    }),
    [endDateChoice],
  );

  function handleConfirm() {
    setActionSubmitting(true);
    setActionError(null);

    let request;
    let successMessage;
    if (pendingAction === "activate") {
      request = activateTenancy(id);
      successMessage = "Tenancy activated.";
    } else if (pendingAction === "end") {
      request = endTenancy(id, endDateChoice || null);
      successMessage = "Tenancy ended.";
    } else {
      request = cancelTenancy(id);
      successMessage = "Tenancy cancelled.";
    }

    request
      .then(() => {
        setToast(successMessage);
        loadTenancy();
      })
      .catch((err) => setActionError(getErrorMessage(err)))
      .finally(() => {
        setPendingAction(null);
        setActionSubmitting(false);
      });
  }

  if (loading) {
    return <LoadingSpinner label="Loading tenancy…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadTenancy} />;
  }

  const canActivate = tenancy.TenancyStatus === "Draft";
  const canEnd = tenancy.TenancyStatus === "Active" || tenancy.TenancyStatus === "Ending Soon";
  const canCancel = tenancy.TenancyStatus !== "Ended" && tenancy.TenancyStatus !== "Cancelled";
  const canEdit = tenancy.TenancyStatus === "Draft";
  const activeDialog = pendingAction ? dialogConfig[pendingAction] : null;

  return (
    <div>
      <PageHeader
        title={`${tenancy.PropertyReference} — ${tenancy.TenantName}`}
        actions={
          <>
            <Link to={`/rent-payments?tenancyId=${id}`} className="button button--secondary">
              Payment history
            </Link>
            {canManage && canEdit && (
              <Link to={`/tenancies/${id}/edit`} className="button button--secondary">
                Edit
              </Link>
            )}
          </>
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
      {actionError && <ErrorMessage message={actionError} />}

      <div className="detail-card">
        <StatusBadge status={tenancy.TenancyStatus} />

        <div className="detail-grid">
          <Field label="Property" value={<Link to={`/properties/${tenancy.PropertyId}`}>{tenancy.PropertyReference}</Link>} />
          <Field label="Tenant" value={<Link to={`/tenants/${tenancy.TenantId}`}>{tenancy.TenantName}</Link>} />
          <Field label="Start date" value={tenancy.StartDate} />
          <Field label="End date" value={tenancy.EndDate} />
          <Field label="Monthly rent" value={`£${tenancy.MonthlyRent}`} />
          <Field label="Deposit" value={`£${tenancy.DepositAmount}`} />
          <Field label="Payment due day" value={tenancy.PaymentDueDay} />
          <Field label="Check-in date" value={tenancy.CheckInDate} />
          <Field label="Check-out date" value={tenancy.CheckOutDate} />
          <Field label="Agreement reference" value={tenancy.AgreementReference} />
          <Field label="Notes" value={tenancy.Notes} />
        </div>

        {canManage && (canActivate || canEnd || canCancel) && (
          <div className="detail-card__actions">
            {canActivate && (
              <button type="button" className="button" onClick={() => setPendingAction("activate")}>
                Activate
              </button>
            )}
            {canEnd && (
              <>
                <DateField
                  label="End date (optional - defaults to today)"
                  name="endDateChoice"
                  value={endDateChoice}
                  onChange={(event) => setEndDateChoice(event.target.value)}
                />
                <button type="button" className="button button--danger" onClick={() => setPendingAction("end")}>
                  End tenancy
                </button>
              </>
            )}
            {canCancel && (
              <button type="button" className="button button--danger" onClick={() => setPendingAction("cancel")}>
                Cancel tenancy
              </button>
            )}
          </div>
        )}

        {tenancy.TenancyStatus === "Ended" && <p>This tenancy has ended.</p>}
        {tenancy.TenancyStatus === "Cancelled" && <p>This tenancy was cancelled.</p>}
      </div>

      <ConfirmationDialog
        open={pendingAction !== null}
        title={activeDialog?.title}
        message={activeDialog?.message}
        confirmLabel={activeDialog?.confirmLabel}
        cancelLabel={activeDialog?.cancelLabel}
        danger={activeDialog?.danger}
        confirmDisabled={actionSubmitting}
        onCancel={() => setPendingAction(null)}
        onConfirm={handleConfirm}
      />

      <p>
        <Link to="/tenancies">← Back to tenancies</Link>
      </p>
    </div>
  );
}
