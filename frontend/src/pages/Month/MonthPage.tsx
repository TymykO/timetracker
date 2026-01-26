/**
 * MonthPage - widok podsumowania miesiąca.
 * TODO: Implementacja tabeli dni z nawigacją między miesiącami.
 */

import { useParams } from "react-router-dom";

export default function MonthPage() {
  const { yearMonth } = useParams<{ yearMonth: string }>();

  return (
    <div style={{ padding: "2rem" }}>
      <h1>Miesiąc: {yearMonth}</h1>
      <p>TODO: Tabela dni z:</p>
      <ul>
        <li>day_type (Working/Free)</li>
        <li>working_time_raw</li>
        <li>overtime</li>
        <li>has_entries</li>
        <li>nawigacja między miesiącami</li>
      </ul>
    </div>
  );
}
