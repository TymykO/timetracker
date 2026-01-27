/**
 * DayPage - widok edycji dnia (wpisy czasu).
 * 
 * TODO: Pełna implementacja filtrów, listy tasków i selected tasks.
 * Na razie podstawowa struktura MUI z placeholderem.
 */

import { useParams, useNavigate } from "react-router-dom";
import { Button, Paper, Typography, List, ListItem, ListItemText, Stack } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Page } from "../../components/Page";

// Helper: formatowanie daty na czytelny format
function formatDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  const day = date.getDate();
  const monthNames = [
    "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
    "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"
  ];
  const month = monthNames[date.getMonth()];
  const year = date.getFullYear();
  const weekdayNames = ["Niedziela", "Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota"];
  const weekday = weekdayNames[date.getDay()];
  return `${weekday}, ${day} ${month} ${year}`;
}

export default function DayPage() {
  const { date } = useParams<{ date: string }>();
  const navigate = useNavigate();

  // Wróć do widoku miesiąca
  const handleBack = () => {
    if (date) {
      const [year, month] = date.split("-");
      navigate(`/month/${year}-${month}`);
    }
  };

  const actions = (
    <Button
      variant="outlined"
      startIcon={<ArrowBackIcon />}
      onClick={handleBack}
    >
      Powrót do miesiąca
    </Button>
  );

  return (
    <Page title={date ? formatDate(date) : "Dzień"} actions={actions}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Implementacja w trakcie
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Ta strona będzie zawierać:
        </Typography>
        <List>
          <ListItem>
            <ListItemText
              primary="Filtry"
              secondary="Filtrowanie tasków według: project_phase, department, discipline + wyszukiwanie tekstowe"
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Lista aktywnych tasków"
              secondary="Wyświetlanie dostępnych tasków z możliwością dodania do selected"
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Selected tasks"
              secondary="Lista wybranych tasków z polami do wprowadzania czasu pracy"
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Przycisk zapisu"
              secondary="Zapisanie wpisów czasu dla dnia"
            />
          </ListItem>
        </List>
        
        <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
          <Button variant="contained" disabled>
            Zapisz wpisy
          </Button>
          <Button variant="outlined" onClick={handleBack}>
            Anuluj
          </Button>
        </Stack>
      </Paper>
    </Page>
  );
}
