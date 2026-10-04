import React from 'react';

const DEPARTMENTS = [
  'Engineering',
  'Operations',
  'Legal & Compliance',
  'Finance',
  'Human Resources',
  'Product & Design',
  'Security & IT',
  'Research',
];

const STATUSES = ['UPLOADED', 'PROCESSING', 'READY', 'FAILED'];
const ACCESS_LEVELS = ['public', 'internal', 'confidential', 'restricted'];

export const DocumentFilters = ({
  filters,
  onFilterChange,
  onResetFilters,
  onRefresh,
  onOpenUpload,
  isLoading,
}) => {
  const hasActiveFilters = Boolean(
    filters.department || filters.status || filters.access_level
  );

  const handleSelectChange = (key, value) => {
    onFilterChange({
      ...filters,
      [key]: value || undefined,
    });
  };

  return (
    <div className="document-filters-container">
      <div className="filter-controls-row">
        {/* Department Filter */}
        <div className="filter-item">
          <label htmlFor="filter-department" className="filter-label">
            Department
          </label>
          <select
            id="filter-department"
            className="filter-select"
            value={filters.department || ''}
            onChange={(e) => handleSelectChange('department', e.target.value)}
          >
            <option value="">All Departments</option>
            {DEPARTMENTS.map((dept) => (
              <option key={dept} value={dept}>
                {dept}
              </option>
            ))}
          </select>
        </div>

        {/* Status Filter */}
        <div className="filter-item">
          <label htmlFor="filter-status" className="filter-label">
            Processing Status
          </label>
          <select
            id="filter-status"
            className="filter-select"
            value={filters.status || ''}
            onChange={(e) => handleSelectChange('status', e.target.value)}
          >
            <option value="">All Statuses</option>
            {STATUSES.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </div>

        {/* Access Level Filter */}
        <div className="filter-item">
          <label htmlFor="filter-access-level" className="filter-label">
            Access Level
          </label>
          <select
            id="filter-access-level"
            className="filter-select"
            value={filters.access_level || ''}
            onChange={(e) => handleSelectChange('access_level', e.target.value)}
          >
            <option value="">All Access Levels</option>
            {ACCESS_LEVELS.map((lvl) => (
              <option key={lvl} value={lvl}>
                {lvl.charAt(0).toUpperCase() + lvl.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Clear Filters Action */}
        {hasActiveFilters && (
          <button
            type="button"
            className="btn-filter-reset"
            onClick={onResetFilters}
            id="btn-clear-filters"
            title="Reset all filters to default"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
            Clear Filters
          </button>
        )}
      </div>

      <div className="filter-actions-row">
        <button
          type="button"
          className="btn-secondary"
          onClick={onRefresh}
          disabled={isLoading}
          id="btn-refresh-documents"
          title="Reload document list from server"
        >
          <svg
            className={isLoading ? 'spinning' : ''}
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
          <span>Refresh</span>
        </button>

        <button
          type="button"
          className="btn-primary"
          onClick={onOpenUpload}
          id="btn-open-upload-modal"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>Upload Document</span>
        </button>
      </div>
    </div>
  );
};

export default DocumentFilters;
