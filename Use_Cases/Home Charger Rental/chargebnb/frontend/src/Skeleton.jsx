/**
 * Skeleton Loader Component
 * Shows placeholder content while data is loading
 */

export function SkeletonCard() {
  return (
    <article className="card skeleton-card">
      <div className="card-head">
        <div>
          <div className="skeleton skeleton-title"></div>
          <div className="skeleton skeleton-subtitle"></div>
        </div>
      </div>
      <div className="card-meta">
        <div>
          <span className="skeleton skeleton-text"></span>
          <div className="skeleton skeleton-value"></div>
        </div>
        <div>
          <span className="skeleton skeleton-text"></span>
          <div className="skeleton skeleton-value"></div>
        </div>
        <div>
          <span className="skeleton skeleton-text"></span>
          <div className="skeleton skeleton-value"></div>
        </div>
      </div>
      <div className="card-footer">
        <div className="skeleton skeleton-chip"></div>
        <div className="skeleton skeleton-button"></div>
      </div>
    </article>
  );
}

export function SkeletonCardGrid({ count = 6 }) {
  return (
    <div className="cards">
      {Array(count)
        .fill(0)
        .map((_, i) => (
          <SkeletonCard key={i} />
        ))}
    </div>
  );
}

export function SkeletonBookingCard() {
  return (
    <div className="booking-card skeleton-booking-card">
      <div className="booking-card-header">
        <div>
          <div className="skeleton skeleton-eyebrow"></div>
          <div className="skeleton skeleton-title"></div>
          <div className="skeleton skeleton-subtitle"></div>
        </div>
        <div className="skeleton skeleton-badge"></div>
      </div>

      <div className="pricing-grid">
        <div>
          <div className="skeleton skeleton-text"></div>
          <div className="skeleton skeleton-value"></div>
        </div>
        <div>
          <div className="skeleton skeleton-text"></div>
          <div className="skeleton skeleton-value"></div>
        </div>
        <div>
          <div className="skeleton skeleton-text"></div>
          <div className="skeleton skeleton-value"></div>
        </div>
      </div>

      <div className="skeleton skeleton-price-mode"></div>
    </div>
  );
}

export function SkeletonBookingEntry() {
  return (
    <div className="booking-entry skeleton-booking-entry">
      <div>
        <div className="skeleton skeleton-text"></div>
        <div className="skeleton skeleton-text skeleton-muted"></div>
      </div>
      <div className="booking-meta">
        <div className="skeleton skeleton-text"></div>
        <div className="skeleton skeleton-value"></div>
      </div>
    </div>
  );
}

export function SkeletonBookingList({ count = 3 }) {
  return (
    <div className="booking-list">
      {Array(count)
        .fill(0)
        .map((_, i) => (
          <SkeletonBookingEntry key={i} />
        ))}
    </div>
  );
}

export function LoadingSpinner() {
  return (
    <div className="loading-spinner">
      <div className="spinner"></div>
      <p>Loading...</p>
    </div>
  );
}
