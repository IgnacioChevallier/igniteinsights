/**
 * Operational timestamps are shown in Argentina time regardless of the browser or
 * server locale. Córdoba and Buenos Aires currently share UTC-3 with no daylight-saving
 * changes, but using the IANA zone keeps historical dates correct as well.
 */
export const ARGENTINA_TIME_ZONE = "America/Argentina/Cordoba";
export const ARGENTINA_TIME_ZONE_LABEL = "ART";

const ARGENTINA_DATE_TIME_FORMATTER = new Intl.DateTimeFormat("es-AR", {
  timeZone: ARGENTINA_TIME_ZONE,
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

export function formatArgentinaDateTime(value: string | Date): string {
  return ARGENTINA_DATE_TIME_FORMATTER.format(typeof value === "string" ? new Date(value) : value);
}
