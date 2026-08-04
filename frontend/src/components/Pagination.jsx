/**
 * Prev/next pager matching the shape of every backend list endpoint's
 * PaginatedResponse (page, page_size, total_items, total_pages - see
 * backend/app/schemas/common.py). Deliberately just prev/next + a range
 * label, not a row of individual page-number buttons - simpler to build
 * and reason about, and every module's list page needs the same thing.
 */
export function Pagination({ page, pageSize, totalItems, totalPages, onPageChange }) {
  if (totalItems === 0) {
    return null;
  }

  const rangeStart = (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(page * pageSize, totalItems);

  return (
    <nav className="pagination" aria-label="Pagination">
      <span className="pagination__summary">
        Showing {rangeStart}-{rangeEnd} of {totalItems}
      </span>
      <div className="pagination__controls">
        <button
          type="button"
          className="button button--secondary"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <span aria-live="polite">
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          className="button button--secondary"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </nav>
  );
}
