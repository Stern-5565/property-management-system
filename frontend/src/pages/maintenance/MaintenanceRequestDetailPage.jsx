/**
 * GET /api/maintenance-requests/{id}, plus every action this module
 * supports. Permission shape mirrors MaintenanceService exactly (see its
 * own docstring):
 *   - canManage (Administrator/PropertyManager): edit/assign/change-
 *     priority/cancel.
 *   - canUpdateWork adds MaintenanceEmployee, but ONLY for their own
 *     assigned request - `isAssignedToMe` reproduces
 *     `_assert_can_update_work`'s ownership check client-side (comparing
 *     `user.EmployeeId` to `request.AssignedEmployeeId`), since a route-
 *     level role list alone can't express "this role, but only their own
 *     rows". Getting this wrong wouldn't be a security hole (the backend
 *     enforces it regardless) but would show controls that 403 on click.
 *   - Terminal states (Completed/Cancelled) hide edit/assign/priority/
 *     status - Enter Costs is the one exception, allowed after Completed
 *     (correcting an actual cost afterward is legitimate), only blocked
 *     once Cancelled. Add Note has no terminal restriction at all in the
 *     backend, so it's always available to anyone who can update work.
 *
 * Assign/Change priority/Change status/Add note/Enter costs are direct,
 * un-confirmed mini-forms (reversible or additive, same reasoning as
 * PropertyDetailPage's status change and RentPaymentDetailPage's
 * record-payment). Complete and Cancel are the two the scope doc
 * explicitly calls out for confirmation - they share one
 * ConfirmationDialog via a `pendingAction` state, same pattern as
 * TenancyDetailPage's activate/end/cancel. Complete's required
 * ResolutionNotes/optional CompletedDate/ActualCost are filled in BEFORE
 * the dialog opens (ConfirmationDialog's `message` renders inside a
 * `<p>`, no slot for embedded form controls - same constraint that
 * shaped Tenancy's "End tenancy" flow).
 *
 * Property/Tenancy/Tenant/Assigned-employee cross-links only render as
 * real links when the viewer's role can actually view that module -
 * the first module where that matters, since MaintenanceEmployee can see
 * THIS page but is excluded from CAN_VIEW_PROPERTIES/TENANTS/TENANCIES/
 * EMPLOYEES entirely (every earlier module's viewers shared the same
 * three-tier role shape, so this mismatch never came up before).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { SelectField } from "../../components/SelectField";
import { FormField } from "../../components/FormField";
import { DateField } from "../../components/DateField";
import { CurrencyField } from "../../components/CurrencyField";
import { ConfirmationDialog } from "../../components/ConfirmationDialog";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import {
  CAN_MANAGE_MAINTENANCE,
  CAN_UPDATE_MAINTENANCE_WORK,
  CAN_VIEW_PROPERTIES,
  CAN_VIEW_TENANTS,
  CAN_VIEW_TENANCIES,
  CAN_VIEW_EMPLOYEES,
} from "../../constants/roles";
import { CHANGEABLE_STATUS_OPTIONS } from "../../constants/maintenanceOptions";
import {
  getRequest,
  assignEmployee,
  changePriority,
  changeStatus,
  addNote,
  enterCosts,
  completeRequest,
  cancelRequest,
} from "../../services/maintenanceService";
import { listEmployees } from "../../services/employeeService";
import { getErrorMessage } from "../../utilities/apiError";

const PRIORITY_CHOICE_OPTIONS = [
  { value: "Low", label: "Low" },
  { value: "Medium", label: "Medium" },
  { value: "High", label: "High" },
  { value: "Emergency", label: "Emergency" },
];

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

const TODAY = new Date().toISOString().slice(0, 10);

export function MaintenanceRequestDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_MAINTENANCE);
  const canSeeProperties = hasAnyRole(user, CAN_VIEW_PROPERTIES);
  const canSeeTenants = hasAnyRole(user, CAN_VIEW_TENANTS);
  const canSeeTenancies = hasAnyRole(user, CAN_VIEW_TENANCIES);
  const canSeeEmployees = hasAnyRole(user, CAN_VIEW_EMPLOYEES);
  const navigate = useNavigate();
  const location = useLocation();

  const [request, setRequest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);
  const [employeeOptions, setEmployeeOptions] = useState([]);

  const [assignEmployeeId, setAssignEmployeeId] = useState("");
  const [assignSubmitting, setAssignSubmitting] = useState(false);
  const [assignError, setAssignError] = useState(null);

  const [priorityChoice, setPriorityChoice] = useState("");
  const [prioritySubmitting, setPrioritySubmitting] = useState(false);
  const [priorityError, setPriorityError] = useState(null);

  const [statusChoice, setStatusChoice] = useState("");
  const [statusSubmitting, setStatusSubmitting] = useState(false);
  const [statusError, setStatusError] = useState(null);

  const [noteText, setNoteText] = useState("");
  const [noteSubmitting, setNoteSubmitting] = useState(false);
  const [noteError, setNoteError] = useState(null);

  const [costsForm, setCostsForm] = useState({ EstimatedCost: "", ActualCost: "" });
  const [costsErrors, setCostsErrors] = useState({});
  const [costsSubmitting, setCostsSubmitting] = useState(false);
  const [costsError, setCostsError] = useState(null);

  const [completeForm, setCompleteForm] = useState({ CompletedDate: "", ResolutionNotes: "", ActualCost: "" });
  const [completeErrors, setCompleteErrors] = useState({});
  const [cancelNotes, setCancelNotes] = useState("");
  const [pendingAction, setPendingAction] = useState(null); // "complete" | "cancel" | null
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const [actionError, setActionError] = useState(null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadRequest = useCallback(() => {
    setLoading(true);
    setError(null);
    getRequest(id)
      .then((data) => {
        setRequest(data);
        setPriorityChoice(data.Priority);
        setStatusChoice(CHANGEABLE_STATUS_OPTIONS.some((o) => o.value === data.MaintenanceStatus) ? data.MaintenanceStatus : "");
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadRequest();
  }, [loadRequest]);

  useEffect(() => {
    if (canManage) {
      listEmployees({ pageSize: 100, isActive: true }).then((data) =>
        setEmployeeOptions(data.items.map((e) => ({ value: String(e.EmployeeId), label: `${e.FirstName} ${e.LastName}` }))),
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canManage]);

  const isAssignedToMe = user?.EmployeeId === request?.AssignedEmployeeId;
  const canUpdateWork = hasAnyRole(user, CAN_UPDATE_MAINTENANCE_WORK) && (canManage || isAssignedToMe);
  const isTerminal = request?.MaintenanceStatus === "Completed" || request?.MaintenanceStatus === "Cancelled";
  const canEdit = canManage && !isTerminal;
  const canAssign = canManage && !isTerminal;
  const canChangePriority = canManage && !isTerminal;
  const canCancel = canManage && request?.MaintenanceStatus !== "Completed" && request?.MaintenanceStatus !== "Cancelled";
  const canChangeStatus = canUpdateWork && !isTerminal;
  const canAddNote = canUpdateWork;
  const canEnterCosts = canUpdateWork && request?.MaintenanceStatus !== "Cancelled";
  const canComplete = canUpdateWork && request?.MaintenanceStatus !== "Completed" && request?.MaintenanceStatus !== "Cancelled";

  function handleAssign(event) {
    event.preventDefault();
    if (!assignEmployeeId) {
      setAssignError("Choose an employee.");
      return;
    }
    setAssignSubmitting(true);
    setAssignError(null);
    assignEmployee(id, Number(assignEmployeeId))
      .then(() => {
        setToast("Employee assigned.");
        setAssignEmployeeId("");
        loadRequest();
      })
      .catch((err) => setAssignError(getErrorMessage(err)))
      .finally(() => setAssignSubmitting(false));
  }

  function handleChangePriority(event) {
    event.preventDefault();
    setPrioritySubmitting(true);
    setPriorityError(null);
    changePriority(id, priorityChoice)
      .then(() => {
        setToast("Priority updated.");
        loadRequest();
      })
      .catch((err) => setPriorityError(getErrorMessage(err)))
      .finally(() => setPrioritySubmitting(false));
  }

  function handleChangeStatus(event) {
    event.preventDefault();
    setStatusSubmitting(true);
    setStatusError(null);
    changeStatus(id, statusChoice)
      .then(() => {
        setToast("Status updated.");
        loadRequest();
      })
      .catch((err) => setStatusError(getErrorMessage(err)))
      .finally(() => setStatusSubmitting(false));
  }

  function handleAddNote(event) {
    event.preventDefault();
    if (!noteText.trim()) {
      setNoteError("Enter a note.");
      return;
    }
    setNoteSubmitting(true);
    setNoteError(null);
    addNote(id, noteText.trim())
      .then(() => {
        setToast("Note added.");
        setNoteText("");
        loadRequest();
      })
      .catch((err) => setNoteError(getErrorMessage(err)))
      .finally(() => setNoteSubmitting(false));
  }

  function handleEnterCosts(event) {
    event.preventDefault();
    const errors = {};
    if (costsForm.EstimatedCost === "" && costsForm.ActualCost === "") {
      errors._form = "Enter an estimated cost, an actual cost, or both.";
    }
    setCostsErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }
    setCostsSubmitting(true);
    setCostsError(null);
    enterCosts(id, { estimatedCost: costsForm.EstimatedCost || null, actualCost: costsForm.ActualCost || null })
      .then(() => {
        setToast("Costs updated.");
        setCostsForm({ EstimatedCost: "", ActualCost: "" });
        loadRequest();
      })
      .catch((err) => setCostsError(getErrorMessage(err)))
      .finally(() => setCostsSubmitting(false));
  }

  function handleOpenComplete() {
    const errors = {};
    if (!completeForm.ResolutionNotes.trim()) {
      errors.ResolutionNotes = "Resolution notes are required to complete a request.";
    }
    setCompleteErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }
    setPendingAction("complete");
  }

  const dialogConfig = useMemo(
    () => ({
      complete: {
        title: "Complete this request?",
        message: `Marks the request Completed as of ${completeForm.CompletedDate || "today"}. This is a one-way door - it can no longer be edited, reassigned, or have its status/priority changed afterward (cost corrections stay possible).`,
        confirmLabel: "Complete request",
        cancelLabel: "Cancel",
        danger: false,
      },
      cancel: {
        title: "Cancel this request?",
        message: "This cannot be undone. The request will be marked Cancelled and can no longer be edited or acted on.",
        confirmLabel: "Cancel request",
        cancelLabel: "Go back",
        danger: true,
      },
    }),
    [completeForm.CompletedDate],
  );

  function handleConfirm() {
    setActionSubmitting(true);
    setActionError(null);

    const request_ =
      pendingAction === "complete"
        ? completeRequest(id, {
            completedDate: completeForm.CompletedDate || null,
            resolutionNotes: completeForm.ResolutionNotes.trim(),
            actualCost: completeForm.ActualCost || null,
          })
        : cancelRequest(id, cancelNotes || null);

    request_
      .then(() => {
        setToast(pendingAction === "complete" ? "Request completed." : "Request cancelled.");
        loadRequest();
      })
      .catch((err) => setActionError(getErrorMessage(err)))
      .finally(() => {
        setPendingAction(null);
        setActionSubmitting(false);
      });
  }

  if (loading) {
    return <LoadingSpinner label="Loading maintenance request…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadRequest} />;
  }

  const activeDialog = pendingAction ? dialogConfig[pendingAction] : null;

  return (
    <div>
      <PageHeader
        title={`${request.RequestReference} — ${request.Title}`}
        actions={
          canManage &&
          canEdit && (
            <Link to={`/maintenance/${id}/edit`} className="button button--secondary">
              Edit
            </Link>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
      {actionError && <ErrorMessage message={actionError} />}

      <div className={"detail-card" + (request.IsEmergency ? " detail-card--emergency" : "")}>
        <StatusBadge status={request.MaintenanceStatus} />{" "}
        <StatusBadge status={request.Priority} />
        {request.IsEmergency && <StatusBadge status="Emergency request" tone="danger" />}

        <div className="detail-grid">
          <Field
            label="Property"
            value={canSeeProperties ? <Link to={`/properties/${request.PropertyId}`}>{request.PropertyReference}</Link> : request.PropertyReference}
          />
          <Field
            label="Tenancy"
            value={
              request.TenancyId
                ? canSeeTenancies
                  ? <Link to={`/tenancies/${request.TenancyId}`}>{request.AgreementReference ?? `#${request.TenancyId}`}</Link>
                  : (request.AgreementReference ?? `#${request.TenancyId}`)
                : null
            }
          />
          <Field
            label="Tenant"
            value={
              request.TenantId
                ? canSeeTenants
                  ? <Link to={`/tenants/${request.TenantId}`}>{request.TenantName}</Link>
                  : request.TenantName
                : null
            }
          />
          <Field
            label="Assigned to"
            value={
              request.AssignedEmployeeId
                ? canSeeEmployees
                  ? <Link to={`/employees/${request.AssignedEmployeeId}`}>{request.AssignedEmployeeName}</Link>
                  : request.AssignedEmployeeName
                : "Unassigned"
            }
          />
          <Field label="Category" value={request.Category} />
          <Field label="Reported date" value={request.ReportedDate} />
          <Field label="Scheduled date" value={request.ScheduledDate} />
          <Field label="Completed date" value={request.CompletedDate} />
          <Field label="Estimated cost" value={request.EstimatedCost !== null ? `£${request.EstimatedCost}` : null} />
          <Field label="Actual cost" value={request.ActualCost !== null ? `£${request.ActualCost}` : null} />
          <Field label="Description" value={request.Description} />
          <Field label="Resolution notes" value={request.ResolutionNotes} />
        </div>

        {canAssign && (
          <>
            <h2 className="detail-card__subheading">Assign employee</h2>
            {assignError && <ErrorMessage message={assignError} />}
            <form onSubmit={handleAssign}>
              <div className="detail-card__actions">
                <SelectField
                  label="Employee"
                  name="assignEmployeeId"
                  value={assignEmployeeId}
                  onChange={(event) => setAssignEmployeeId(event.target.value)}
                  placeholder="Choose an employee"
                  options={employeeOptions}
                />
                <button type="submit" className="button" disabled={assignSubmitting}>
                  {assignSubmitting ? "Assigning…" : "Assign"}
                </button>
              </div>
            </form>
          </>
        )}

        {canChangePriority && (
          <>
            <h2 className="detail-card__subheading">Change priority</h2>
            {priorityError && <ErrorMessage message={priorityError} />}
            <form onSubmit={handleChangePriority}>
              <div className="detail-card__actions">
                <SelectField
                  label="Priority"
                  name="priorityChoice"
                  value={priorityChoice}
                  onChange={(event) => setPriorityChoice(event.target.value)}
                  options={PRIORITY_CHOICE_OPTIONS}
                />
                <button type="submit" className="button" disabled={prioritySubmitting || priorityChoice === request.Priority}>
                  {prioritySubmitting ? "Updating…" : "Update priority"}
                </button>
              </div>
            </form>
          </>
        )}

        {canChangeStatus && (
          <>
            <h2 className="detail-card__subheading">Change status</h2>
            {statusError && <ErrorMessage message={statusError} />}
            <form onSubmit={handleChangeStatus}>
              <div className="detail-card__actions">
                <SelectField
                  label="Status"
                  name="statusChoice"
                  value={statusChoice}
                  onChange={(event) => setStatusChoice(event.target.value)}
                  options={CHANGEABLE_STATUS_OPTIONS}
                />
                <button
                  type="submit"
                  className="button"
                  disabled={statusSubmitting || !statusChoice || statusChoice === request.MaintenanceStatus}
                >
                  {statusSubmitting ? "Updating…" : "Update status"}
                </button>
              </div>
            </form>
          </>
        )}

        {canEnterCosts && (
          <>
            <h2 className="detail-card__subheading">Enter costs</h2>
            {costsErrors._form && <ErrorMessage message={costsErrors._form} />}
            {costsError && <ErrorMessage message={costsError} />}
            <form onSubmit={handleEnterCosts} noValidate>
              <div className="form-grid">
                <CurrencyField
                  label="Estimated cost"
                  name="EstimatedCost"
                  value={costsForm.EstimatedCost}
                  onChange={(event) => setCostsForm((prev) => ({ ...prev, EstimatedCost: event.target.value }))}
                />
                <CurrencyField
                  label="Actual cost"
                  name="ActualCost"
                  value={costsForm.ActualCost}
                  onChange={(event) => setCostsForm((prev) => ({ ...prev, ActualCost: event.target.value }))}
                />
              </div>
              <div className="form-card__actions">
                <button type="submit" className="button" disabled={costsSubmitting}>
                  {costsSubmitting ? "Saving…" : "Save costs"}
                </button>
              </div>
            </form>
          </>
        )}

        {canAddNote && (
          <>
            <h2 className="detail-card__subheading">Add a note</h2>
            {noteError && <ErrorMessage message={noteError} />}
            <form onSubmit={handleAddNote} noValidate>
              <FormField label="Note" name="noteText" value={noteText} onChange={(event) => setNoteText(event.target.value)} />
              <div className="form-card__actions">
                <button type="submit" className="button" disabled={noteSubmitting}>
                  {noteSubmitting ? "Adding…" : "Add note"}
                </button>
              </div>
            </form>
          </>
        )}

        {canComplete && (
          <>
            <h2 className="detail-card__subheading">Complete request</h2>
            <div className="form-grid">
              <DateField
                label="Completed date (optional - defaults to today)"
                name="CompletedDate"
                value={completeForm.CompletedDate}
                onChange={(event) => setCompleteForm((prev) => ({ ...prev, CompletedDate: event.target.value }))}
                max={TODAY}
              />
              <CurrencyField
                label="Actual cost (optional)"
                name="CompleteActualCost"
                value={completeForm.ActualCost}
                onChange={(event) => setCompleteForm((prev) => ({ ...prev, ActualCost: event.target.value }))}
              />
              <div className="form-field--full">
                <FormField
                  label="Resolution notes"
                  name="ResolutionNotes"
                  value={completeForm.ResolutionNotes}
                  onChange={(event) => setCompleteForm((prev) => ({ ...prev, ResolutionNotes: event.target.value }))}
                  required
                  error={completeErrors.ResolutionNotes}
                />
              </div>
            </div>
            <div className="detail-card__actions">
              <button type="button" className="button" onClick={handleOpenComplete}>
                Complete request
              </button>
            </div>
          </>
        )}

        {canCancel && (
          <>
            <h2 className="detail-card__subheading">Cancel request</h2>
            <FormField
              label="Cancellation notes (optional)"
              name="cancelNotes"
              value={cancelNotes}
              onChange={(event) => setCancelNotes(event.target.value)}
            />
            <div className="detail-card__actions">
              <button type="button" className="button button--danger" onClick={() => setPendingAction("cancel")}>
                Cancel request
              </button>
            </div>
          </>
        )}

        {request.MaintenanceStatus === "Completed" && <p>This request has been completed.</p>}
        {request.MaintenanceStatus === "Cancelled" && <p>This request has been cancelled.</p>}

        <h2 className="detail-card__subheading">Timeline</h2>
        {request.Notes.length === 0 ? (
          <p>No notes yet.</p>
        ) : (
          <ul className="timeline">
            {request.Notes.map((note) => (
              <li key={note.MaintenanceNoteId} className="timeline__item">
                <div className="timeline__meta">
                  {note.EmployeeName} — {note.CreatedAt}
                </div>
                <p className="timeline__text">{note.NoteText}</p>
              </li>
            ))}
          </ul>
        )}
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
        <Link to="/maintenance">← Back to maintenance requests</Link>
      </p>
    </div>
  );
}
