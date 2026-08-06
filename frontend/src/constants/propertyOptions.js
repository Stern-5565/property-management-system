/**
 * Mirrors backend/app/schemas/property.py's PropertyTypeValue/
 * PropertyStatusValue Literal definitions. Used by both
 * PropertiesListPage (filter) and PropertyFormPage/PropertyDetailPage
 * (create/edit/status-change) - kept in one place so the two stay in
 * sync if the backend's enum ever changes.
 */
export const PROPERTY_TYPE_OPTIONS = [
  { value: "House", label: "House" },
  { value: "Flat", label: "Flat" },
  { value: "Bungalow", label: "Bungalow" },
  { value: "Studio", label: "Studio" },
  { value: "Maisonette", label: "Maisonette" },
  { value: "Other", label: "Other" },
];

export const PROPERTY_STATUS_OPTIONS = [
  { value: "Vacant", label: "Vacant" },
  { value: "Occupied", label: "Occupied" },
  { value: "Under Maintenance", label: "Under Maintenance" },
  { value: "Unavailable", label: "Unavailable" },
  { value: "Archived", label: "Archived" },
];
