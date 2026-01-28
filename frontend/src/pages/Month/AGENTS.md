# TimeTracker — AGENTS (FRONTEND / Month Page)

> Scope: `frontend/src/pages/Month/`  
> This file defines the **exact UX + state rules** for the Month view.  
> It overrides/extends `frontend/AGENTS.md` and `root AGENTS.md` for this subtree.

---

## 0) Purpose of Month view (MVP)

Month view is the overview screen for timesheet entries. For a selected month, the user can:
- view a calendar table of all days in the month
- see working time and overtime per day
- identify days with entries (has_entries indicator)
- navigate between months (prev/next)
- click on a day to open Day view for editing

Backend is the source of truth; frontend displays computed data and provides navigation.

---

## 1) Route and navigation rules

### Route
- Path: `/month/:yyyy-mm`
- Default: `/month` redirects to current month (`YYYY-MM`)

### Navigation
- User can navigate **back/forward by month** within allowed range:
  - **Cannot navigate to future months** (blocked in backend)
  - Can navigate to current month and all past months
  - Navigation buttons adjust based on current month

### Buttons
- "Poprzedni miesiąc" (Previous month): Always enabled (can go infinitely back)
- "Następny miesiąc" (Next month): Disabled if current month (cannot go to future)
- Month header shows: "Nazwa_Miesiąca YYYY" (e.g., "Marzec 2025")

---

## 2) Data that must be loaded

On page load (and when month changes), fetch:

**Month summary**:
- `GET /api/timesheet/month?month=YYYY-MM`
- returns:
  - `month`: "YYYY-MM" string
  - `days[]`: Array of day objects with:
    - `date`: "YYYY-MM-DD"
    - `day_type`: "Working" | "Free"
    - `working_time_raw_minutes`: int (sum of entries for that day)
    - `overtime_minutes`: int (computed by backend)
    - `has_entries`: bool (true if any entries exist)
    - `is_future`: bool (true if date > today)
    - `is_editable`: bool (true if in editable window: current or previous month)

**Important:**
- Request must use `credentials: "include"`
- If request returns 401 → redirect to `/login`
- If request returns 400 (future month) → show error, disable navigation forward

---

## 3) Local state model

### A) Current month (from URL)
- Extract `yearMonth` from route params: `/month/:yyyy-mm`
- If no param, default to current month

### B) Month summary data
- Loaded from API, stored in component state or React Query cache
- Contains all days for the month (1st to last day)

### C) Totals (derived from days)
- `totalWorkingTime`: sum of `working_time_raw_minutes` for all days
- `totalOvertime`: sum of `overtime_minutes` for all days
- Display in header summary panel

### D) Navigation state
- `canGoNext`: false if current month, true otherwise
- Compute by comparing `yearMonth` with today's month

---

## 4) Month table display rules

### Table columns
1. **Date**: Day number + day name (e.g., "15 Śr" for Wednesday)
2. **Day type**: "Working" | "Free"
3. **Working time**: Display as HH:MM (convert minutes)
4. **Overtime**: Display as HH:MM (convert minutes)
5. **Status**: Badge/indicator if `has_entries === true` (e.g., green checkmark)

### Row styling
- **Future days** (`is_future === true`):
  - Gray text
  - Not clickable (no link to Day view)
  - Disabled appearance
- **Non-editable days** (`is_editable === false`):
  - Normal appearance (can view)
  - Gray text for emphasis
  - Clickable but Day view will show as read-only
- **Editable days** (`is_editable === true`):
  - Normal text color
  - Clickable (link to Day view)
  - Hover effect
- **Days with entries** (`has_entries === true`):
  - Show indicator badge (e.g., green "✓")
  - Bold or highlighted working time

### Row interaction
- Click on row → navigate to `/day/:yyyy-mm-dd`
- Future days: no link (disabled)
- Past/current days: link active

---

## 5) Summary panel display rules

### Header
- Month name + year (e.g., "Marzec 2025")
- Translated month names in Polish

### Navigation buttons
- "< Poprzedni" (Previous month): Always enabled
- "Następny >" (Next month): Disabled if current month

### Totals
- "Czas pracy: HH:MM" (Total working time for month)
- "Nadgodziny: HH:MM" (Total overtime for month)
- Compute by summing all days' values

**Display format:**
- Minutes → HH:MM (e.g., 9600 minutes → 160:00)
- Allow hours > 24 (e.g., 160:00 for full month)

---

## 6) Navigation behavior

### Previous month
- Subtract 1 month from current `yearMonth`
- Navigate to `/month/:yyyy-mm`
- No restrictions (can go infinitely back)

### Next month
- Add 1 month to current `yearMonth`
- Navigate to `/month/:yyyy-mm`
- **Disabled if current month** (check if yearMonth >= today's month)

### Future month blocking
- If user manually enters future month in URL:
  - Backend returns 400 error
  - Show error message: "Nie można załadować przyszłego miesiąca"
  - Disable "Next" button
  - Allow "Previous" to go back

---

## 7) Date helpers (utility functions)

### `addMonths(yearMonth: string, delta: number): string`
- Add/subtract months from YYYY-MM string
- Handles year rollover (e.g., 2025-12 + 1 → 2026-01)

### `getMonthName(yearMonth: string): string`
- Convert YYYY-MM to "Nazwa_Miesiąca YYYY"
- Use Polish month names: ["Styczeń", "Luty", "Marzec", ...]

### `isMonthInFuture(yearMonth: string): boolean`
- Check if yearMonth > current month
- Used to disable "Next" button

### `formatMinutesToHHMM(minutes: number): string`
- Convert minutes to HH:MM format
- Allow hours > 24 (e.g., 1500 minutes → 25:00)

---

## 8) Component composition

Month page is composed of:
- `Page` wrapper (title + actions)
- `MonthSummaryPanel` (header with month name, totals, navigation)
- `MonthTable` (calendar table of days)
- `LoadingState` (while fetching data)
- `ErrorState` (on fetch error with retry button)

**Layout:**
```tsx
<Page title={getMonthName(yearMonth)} actions={<NavigationButtons />}>
  {isLoading && <LoadingState />}
  {isError && <ErrorState message={error} onRetry={refetch} />}
  {data && (
    <>
      <MonthSummaryPanel
        month={yearMonth}
        totalWorkingTime={totalWorkingTime}
        totalOvertime={totalOvertime}
        onPrevMonth={handlePrevMonth}
        onNextMonth={handleNextMonth}
        canGoNext={!isCurrentMonth}
      />
      <MonthTable
        days={data.days}
        onDayClick={(date) => navigate(`/day/${date}`)}
      />
    </>
  )}
</Page>
```

---

## 9) Error handling

### 400 (Bad Request - future month)
- Show error: "Nie można załadować przyszłego miesiąca."
- Disable "Next" button
- Allow "Previous" to go back to valid month

### 401 (Unauthorized)
- Redirect to `/login`
- Clear React Query cache

### 403 (Forbidden - inactive employee)
- Show error: "Konto nieaktywne. Skontaktuj się z administratorem."

### Network / 500 errors
- Show error: "Nie udało się załadować danych miesiąca. Spróbuj ponownie."
- Provide retry button
- Keep user state intact (don't navigate away)

---

## 10) Cache invalidation

### When to invalidate Month cache
- After saving Day view: Invalidate `['month', yearMonth]` query
  - Ensures totals and has_entries indicators update
- After navigating to new month: Fetch new data (automatic)

### Query keys
- Month summary: `['month', yearMonth]` (e.g., `['month', '2025-03']`)
- User profile: `['me']` (shared across all pages)

---

## 11) Loading and error states

### Loading
- Show `<LoadingState message="Ładowanie danych miesiąca..." />`
- Centered spinner
- Hide month table and summary panel

### Error
- Show `<ErrorState message={error} onRetry={refetch} />`
- Display error message from API or generic message
- Provide "Spróbuj ponownie" (Retry) button

### Empty state (no entries for month)
- Still show month table (all days with 0 time)
- Totals will be 00:00
- No special "empty" message needed (table shows structure)

---

## 12) Accessibility considerations

### Keyboard navigation
- Month table rows are focusable (clickable links)
- Tab order: Previous button → Next button → table rows
- Enter/Space on row → navigate to day

### Screen reader
- Month header announces: "Marzec 2025"
- Table has proper `<thead>` with column headers
- Disabled buttons have `aria-disabled="true"`
- Future day rows have `aria-disabled="true"` and no link

### Visual indicators
- Future days: grayed out
- Non-editable days: subtle gray
- Editable days: normal text, hover effect
- Has entries: green badge for visibility

---

## 13) Performance optimization

### Minimize re-renders
- Use `useMemo` for computed totals (sum of days)
- Use `useCallback` for navigation handlers

### Avoid unnecessary fetches
- Use React Query cache (don't refetch on revisit)
- Invalidate cache only when needed (after save)

### Table rendering
- Month table has max 31 rows (not a performance issue)
- No virtualization needed for MVP

---

## 14) Definition of Done (Month page)

Month page is MVP-complete when:
- Loads month summary, handles 401 redirect
- Displays calendar table with all days (1st to last)
- Shows totals (working time + overtime) in header
- Navigation buttons work (prev/next, disabled for future)
- Future days are grayed out and not clickable
- Days with entries show indicator badge
- Clicking day navigates to Day view (`/day/:yyyy-mm-dd`)
- Future month blocking works (400 error handled)
- Cache invalidation after Day save works (totals update)

---

## 15) Future enhancements (not MVP)

- **Month picker**: Calendar popup to jump to specific month
- **Year view**: Annual summary with all months
- **Export**: Download month as PDF or CSV
- **Filters**: Show only days with entries, or only working days
- **Bulk operations**: Copy week to week, auto-fill
- **Visual calendar**: Grid view (week rows) instead of table
- **Colors**: Highlight days by overtime level (green/yellow/red)

---

## 16) Related documentation

- **Day page AGENTS.md**: Day view rules and behavior
- **Frontend AGENTS.md**: Frontend architecture and patterns
- **API documentation**: `backend/timetracker_app/api/AGENTS.md`
- **Components README**: `frontend/src/components/README.md`

---

## Summary

Month view provides a high-level overview of timesheet entries for a given month. It serves as the navigation hub, allowing users to see their monthly activity at a glance and drill down into specific days for editing. The view respects domain rules (no future months, editability windows) and keeps the UI simple and performant.
