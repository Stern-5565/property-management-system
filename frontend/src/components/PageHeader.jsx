/**
 * Standard top-of-page banner: a title, an optional one-line description,
 * and an optional slot for page-level actions (e.g. a "+ New Landlord"
 * button). Every module's list/detail page starts with one of these -
 * keeping the title/description/actions layout in one place means every
 * module looks consistent without each page re-inventing the header.
 */
export function PageHeader({ title, description, actions }) {
  return (
    <div className="page-header">
      <div>
        <h1 className="page-header__title">{title}</h1>
        {description && <p className="page-header__description">{description}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </div>
  );
}
