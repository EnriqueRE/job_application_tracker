/** `date` as an ISO calendar date (`YYYY-MM-DD`) in the local time zone, like the API's dates. */
export function toIsoDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

/** Today's local date as `YYYY-MM-DD`. */
export function todayIsoDate(): string {
  return toIsoDate(new Date())
}
