/**
 * Narzędzia do formatowania czasu.
 */

/**
 * Konwertuje minuty na format HH:MM.
 * @param minutes - liczba minut do sformatowania
 * @returns string w formacie HH:MM (np. "08:30", "123:45")
 */
export function minutesToHHMM(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}
