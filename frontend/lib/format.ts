export type DateValue = string | number | null | undefined;

/** Normalize ISO timestamps and Unix seconds/milliseconds for browser Date. */
export function toDate(value: DateValue): Date | null {
  if (value === null || value === undefined || value === "") return null;
  const numeric = typeof value === "number" ? value : /^\d+(?:\.\d+)?$/.test(value) ? Number(value) : null;
  const date = numeric === null
    ? new Date(value)
    : new Date(numeric < 10_000_000_000 ? numeric * 1_000 : numeric);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function timeAgo(value: DateValue): string {
  const date = toDate(value);
  if (!date) return "Time unavailable";
  const minutes = Math.max(0, Math.floor((Date.now() - date.getTime()) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1_440) return `${Math.floor(minutes / 60)}h ago`;
  return `${Math.floor(minutes / 1_440)}d ago`;
}

export function displayDate(value: DateValue): string {
  const date = toDate(value);
  return date ? new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date) : "Date unavailable";
}
