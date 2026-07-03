// Reusable stats card for displaying a single stat (label + value).
// Per ARCH-001@0.1.1 §3 C4: card-based layout.

interface StatsCardProps {
  label: string;
  value: number | string;
  suffix?: string;
}

export function StatsCard({ label, value, suffix }: StatsCardProps) {
  return (
    <div className="stats-card">
      <div className="stats-card-label">{label}</div>
      <div className="stats-card-value">
        {value}
        {suffix && <span className="stats-card-suffix">{suffix}</span>}
      </div>
    </div>
  );
}
