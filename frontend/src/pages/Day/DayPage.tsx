/**
 * DayPage - widok edycji dnia (wpisy czasu).
 * TODO: Implementacja filtrów, listy tasków i selected tasks.
 */

import { useParams } from "react-router-dom";

export default function DayPage() {
  const { date } = useParams<{ date: string }>();

  return (
    <div style={{ padding: "2rem" }}>
      <h1>Dzień: {date}</h1>
      <p>TODO: Implementacja:</p>
      <ul>
        <li>Filtry (project_phase, department, discipline, search)</li>
        <li>Lista aktywnych tasków (z filtrowaniem)</li>
        <li>Selected tasks (z duration inputs)</li>
        <li>Save button</li>
      </ul>
    </div>
  );
}
