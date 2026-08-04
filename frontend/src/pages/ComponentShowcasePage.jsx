/**
 * Internal, dev-only page demonstrating one simple example of each
 * reusable component (documentation/project-scope.md, Prompt 19's
 * "demonstrate each component with one simple example"). Not linked from
 * the sidebar - reach it directly at /dev/components while logged in.
 * Safe to delete once every module has been built and is exercising
 * these components for real; kept as a single reference page for now
 * rather than scattering standalone examples across module code.
 */
import { useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import { KpiCard } from "../components/KpiCard";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { ConfirmationDialog } from "../components/ConfirmationDialog";
import { DataTable } from "../components/DataTable";
import { Pagination } from "../components/Pagination";
import { SearchInput } from "../components/SearchInput";
import { FilterPanel } from "../components/FilterPanel";
import { FormField } from "../components/FormField";
import { SelectField } from "../components/SelectField";
import { DateField } from "../components/DateField";
import { CurrencyField } from "../components/CurrencyField";

const SAMPLE_ROWS = [
  { id: 1, reference: "PM-0001", city: "London", status: "Occupied" },
  { id: 2, reference: "PM-0002", city: "Leeds", status: "Vacant" },
];

function Section({ title, children }) {
  return (
    <section className="showcase-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function ComponentShowcasePage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogResult, setDialogResult] = useState(null);
  const [name, setName] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [startDate, setStartDate] = useState("");
  const [rent, setRent] = useState("");

  return (
    <div>
      <PageHeader
        title="Component library"
        description="One example of every reusable component from Prompt 19. Not part of the real app navigation."
      />

      <Section title="PageHeader">
        <p>This page's own banner, above, is a PageHeader example - title + description + optional actions slot.</p>
      </Section>

      <Section title="StatusBadge">
        <div className="showcase-row">
          <StatusBadge status="Occupied" />
          <StatusBadge status="Overdue" />
          <StatusBadge status="Pending" />
          <StatusBadge status="Cancelled" />
          <StatusBadge status="Custom" tone="info" />
        </div>
      </Section>

      <Section title="KPI card">
        <div className="showcase-row">
          <KpiCard label="Occupied Properties" value="6" hint="of 9 active" />
          <KpiCard label="Outstanding Rent" value="£6,475.00" tone="warning" />
        </div>
      </Section>

      <Section title="LoadingSpinner">
        <LoadingSpinner label="Loading records…" />
      </Section>

      <Section title="ErrorMessage">
        <ErrorMessage message="Could not load properties." onRetry={() => alert("Retry clicked")} />
      </Section>

      <Section title="EmptyState">
        <EmptyState message="No maintenance requests match your filters." />
      </Section>

      <Section title="ConfirmationDialog">
        <button type="button" className="button button--danger" onClick={() => setDialogOpen(true)}>
          Deactivate landlord…
        </button>
        {dialogResult && <p>Last result: {dialogResult}</p>}
        <ConfirmationDialog
          open={dialogOpen}
          title="Deactivate this landlord?"
          message="They have no active properties, so this is safe - but it can't be undone from here."
          confirmLabel="Deactivate"
          danger
          onCancel={() => {
            setDialogOpen(false);
            setDialogResult("cancelled");
          }}
          onConfirm={() => {
            setDialogOpen(false);
            setDialogResult("confirmed");
          }}
        />
      </Section>

      <Section title="SearchInput">
        <SearchInput value={search} onSearch={setSearch} placeholder="Search properties…" />
        <p>Debounced value: "{search}"</p>
      </Section>

      <Section title="FilterPanel">
        <FilterPanel title="Filters" onClear={() => alert("Filters cleared")}>
          <SelectField
            label="Status"
            name="status"
            value=""
            onChange={() => {}}
            placeholder="Any status"
            options={[
              { value: "Occupied", label: "Occupied" },
              { value: "Vacant", label: "Vacant" },
            ]}
          />
        </FilterPanel>
      </Section>

      <Section title="DataTable + Pagination">
        <DataTable
          columns={[
            { key: "reference", header: "Reference" },
            { key: "city", header: "City" },
            { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
          ]}
          rows={SAMPLE_ROWS}
        />
        <Pagination page={page} pageSize={2} totalItems={9} totalPages={5} onPageChange={setPage} />
      </Section>

      <Section title="FormField, SelectField, DateField, CurrencyField">
        <FormField
          label="Property reference"
          name="reference"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
          error={name.length > 0 && name.length < 3 ? "Must be at least 3 characters." : null}
        />
        <SelectField
          label="Property type"
          name="propertyType"
          value={propertyType}
          onChange={(event) => setPropertyType(event.target.value)}
          placeholder="Choose a type"
          options={[
            { value: "House", label: "House" },
            { value: "Flat", label: "Flat" },
          ]}
        />
        <DateField label="Start date" name="startDate" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        <CurrencyField label="Monthly rent" name="rent" value={rent} onChange={(event) => setRent(event.target.value)} />
      </Section>
    </div>
  );
}
