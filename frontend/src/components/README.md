# TimeTracker — Components Library

> Component inventory and usage patterns for the TimeTracker frontend.

---

## Overview

This directory contains reusable React components organized into two categories:
- **Shared components**: Generic UI patterns (layout, error handling, loading)
- **Domain components**: Business-specific components (tasks, timesheet)

**Design system**: Material-UI (MUI) for consistent styling and behavior.

---

## Component Inventory

### Shared Components

#### `AppShell`
**Purpose**: Application-wide layout wrapper

**Responsibilities:**
- AppBar with "TimeTracker" branding
- User email display + logout button (when authenticated)
- Container for page content
- Conditional rendering (hides AppBar on public routes)

**Props:**
```typescript
interface AppShellProps {
  children: React.ReactNode;
}
```

**Usage:**
```tsx
// In router.tsx
<AppShell>
  <Routes>
    <Route path="/month" element={<MonthPage />} />
    <Route path="/day/:date" element={<DayPage />} />
  </Routes>
</AppShell>
```

**Features:**
- Fetches user profile with `useQuery(['me'])`
- Skips API call on public routes (login, set-password, etc.)
- Logout clears React Query cache and redirects to `/login`
- Full-width container with responsive padding

**Public routes (no AppBar):**
- `/login`
- `/set-password`
- `/forgot-password`
- `/reset-password`

---

#### `Page`
**Purpose**: Consistent page layout wrapper

**Responsibilities:**
- Page title (h4)
- Optional action buttons (right-aligned)
- Content area with consistent spacing

**Props:**
```typescript
interface PageProps {
  title: string;
  actions?: React.ReactNode;  // Optional buttons/actions
  children: React.ReactNode;
}
```

**Usage:**
```tsx
<Page 
  title="Miesiąc: Marzec 2025" 
  actions={
    <Button onClick={handlePrevMonth}>Poprzedni miesiąc</Button>
  }
>
  <MonthTable days={days} />
</Page>
```

**Layout:**
- Title and actions in flexbox row (space-between)
- Bottom margin of 3 units between title row and content
- Content area with no constraints (flexible height/width)

---

#### `ErrorState`
**Purpose**: Display error messages

**Responsibilities:**
- Error icon
- Error message display
- Optional retry button

**Props:**
```typescript
interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}
```

**Usage:**
```tsx
{isError && (
  <ErrorState 
    message={error.message} 
    onRetry={refetch} 
  />
)}
```

**Styling:**
- Centered vertically and horizontally
- Red error icon
- Gray secondary text
- Primary-colored retry button

---

#### `LoadingState`
**Purpose**: Display loading spinner

**Responsibilities:**
- Centered CircularProgress spinner
- Optional loading text

**Props:**
```typescript
interface LoadingStateProps {
  message?: string;
}
```

**Usage:**
```tsx
{isLoading && <LoadingState message="Ładowanie danych..." />}
```

**Styling:**
- Centered in available space
- MUI CircularProgress component
- Optional text below spinner

---

### Domain Components

#### `TaskPicker`
**Purpose**: Display list of available tasks with add buttons

**Responsibilities:**
- Render task list with display names
- Show task metadata (project_phase, department, discipline)
- Add button (+) for each task
- Handle disabled state (when day is not editable)
- Scroll for long lists

**Props:**
```typescript
interface TaskPickerProps {
  tasks: Task[];
  onAddTask: (task: Task) => void;
  disabled: boolean;
}
```

**Usage:**
```tsx
<TaskPicker
  tasks={filteredTasks}
  onAddTask={handleAddTask}
  disabled={!day.is_editable}
/>
```

**Features:**
- Max height 500px with scroll
- Border around list
- Hover effect (disabled when not editable)
- Secondary text shows: "project_phase • department • discipline"
- Empty state: "Brak dostępnych tasków"

---

#### `SelectedTasksTable`
**Purpose**: Display and edit selected tasks with durations

**Responsibilities:**
- Table of selected tasks with editable duration inputs
- Delete button (X) for each task
- Hours display (billable hours_decimal)
- Validation feedback (duration must be > 0)
- Handle disabled state

**Props:**
```typescript
interface SelectedTasksTableProps {
  entries: TimeEntry[];
  onUpdateDuration: (taskId: number, minutes: number) => void;
  onRemoveTask: (taskId: number) => void;
  disabled: boolean;
}
```

**Usage:**
```tsx
<SelectedTasksTable
  entries={selectedEntries}
  onUpdateDuration={handleUpdateDuration}
  onRemoveTask={handleRemoveTask}
  disabled={!day.is_editable}
/>
```

**Table columns:**
1. Task name (display_name)
2. Duration input (minutes, TextField)
3. Billable hours (read-only, hours_decimal)
4. Delete button (IconButton with X)

**Features:**
- Duration input: type="number", min=0, required
- Error state for invalid duration (red border)
- Disabled inputs when day is not editable
- Empty state: "Brak wybranych tasków"

---

#### `FiltersBar`
**Purpose**: Filter controls for task list

**Responsibilities:**
- Dropdowns for project_phase, department, discipline
- Free-text search input
- Clear filters button
- Handle filter state changes

**Props:**
```typescript
interface FiltersBarProps {
  filters: TaskFilters;
  filterValues: FilterValues;
  onFilterChange: (filters: TaskFilters) => void;
  disabled: boolean;
}

interface TaskFilters {
  project_phase: string;
  department: string;
  discipline: string;
  search: string;
}

interface FilterValues {
  project_phases: string[];
  departments: string[];
  disciplines: string[];
}
```

**Usage:**
```tsx
<FiltersBar
  filters={filters}
  filterValues={filterValues}
  onFilterChange={setFilters}
  disabled={!day.is_editable}
/>
```

**Features:**
- 3 MUI Select dropdowns (project_phase, department, discipline)
- 1 TextField for free-text search
- "Wyczyść filtry" button (resets all to empty)
- Dropdowns show "Wszystkie" when empty
- Responsive layout (2x2 grid)

**Filtering behavior:**
- All filters are AND combined
- Empty filter = no filtering on that dimension
- Search matches display_name (case-insensitive)
- Filters remain after adding a task (as per AGENTS.md)

---

#### `MonthTable`
**Purpose**: Display calendar table for month view

**Responsibilities:**
- Render calendar grid (days of month)
- Show day number, day type, working time, overtime
- Link to day page (clickable rows)
- Visual indicators (future days grayed out, has_entries badge)
- Responsive layout

**Props:**
```typescript
interface MonthTableProps {
  days: MonthDay[];
  onDayClick: (date: string) => void;
}

interface MonthDay {
  date: string;
  day_type: 'Working' | 'Free';
  working_time_raw_minutes: number;
  overtime_minutes: number;
  has_entries: boolean;
  is_future: boolean;
  is_editable: boolean;
}
```

**Usage:**
```tsx
<MonthTable
  days={monthData.days}
  onDayClick={(date) => navigate(`/day/${date}`)}
/>
```

**Table columns:**
1. Date (DD, day name)
2. Day type (Working / Free)
3. Working time (HH:MM)
4. Overtime (HH:MM)
5. Status (badge if has_entries)

**Features:**
- Clickable rows navigate to day page
- Future days: grayed out, not clickable
- Non-editable days: gray text
- has_entries: green badge "✓"
- Responsive: stacks on mobile

---

#### `MonthSummaryPanel`
**Purpose**: Display month totals summary

**Responsibilities:**
- Show total working time for month
- Show total overtime for month
- Display month/year header
- Navigation buttons (prev/next month)

**Props:**
```typescript
interface MonthSummaryPanelProps {
  month: string;  // YYYY-MM
  totalWorkingTime: number;  // minutes
  totalOvertime: number;  // minutes
  onPrevMonth: () => void;
  onNextMonth: () => void;
  canGoNext: boolean;  // Disable next if current month
}
```

**Usage:**
```tsx
<MonthSummaryPanel
  month="2025-03"
  totalWorkingTime={9600}  // 160 hours
  totalOvertime={300}      // 5 hours
  onPrevMonth={handlePrevMonth}
  onNextMonth={handleNextMonth}
  canGoNext={!isCurrentMonth}
/>
```

**Features:**
- Header: "Marzec 2025"
- Navigation: "< Poprzedni" | "Następny >"
- Totals: "Czas pracy: 160:00" | "Nadgodziny: 5:00"
- Next button disabled if current month (no future months)

---

## Component Composition Patterns

### Page structure
```
<AppShell>
  <Page title="..." actions={...}>
    {isLoading && <LoadingState />}
    {isError && <ErrorState />}
    {data && <DomainComponent />}
  </Page>
</AppShell>
```

### Day page composition
```
<Page title="..." actions={<SaveButton />}>
  <Grid container spacing={2}>
    <Grid item xs={12} md={6}>
      <FiltersBar />
      <TaskPicker />
    </Grid>
    <Grid item xs={12} md={6}>
      <SelectedTasksTable />
      <MonthSummaryPanel />  {/* Day totals */}
    </Grid>
  </Grid>
</Page>
```

### Month page composition
```
<Page title="..." actions={<NavigationButtons />}>
  <MonthSummaryPanel />  {/* Month totals */}
  <MonthTable />
</Page>
```

---

## Material-UI Integration

### Theme usage
- Theme defined in `src/app/theme.ts`
- Components use MUI theme values (spacing, colors, breakpoints)
- Consistent spacing: `sx={{ mb: 3 }}` uses theme.spacing(3)

### Common MUI components used
- `Box`: Layout container
- `Paper`: Card/surface
- `Typography`: Text (h4, h6, body1, body2)
- `Button`, `IconButton`: Actions
- `TextField`: Text inputs
- `Select`, `MenuItem`: Dropdowns
- `Table`, `TableBody`, `TableCell`, `TableHead`, `TableRow`: Tables
- `CircularProgress`: Loading spinner
- `AppBar`, `Toolbar`: Top navigation
- `Container`: Page container
- `Grid`: Responsive layout
- `Stack`: Flex layout

### Responsive patterns
```tsx
// Responsive grid
<Grid container spacing={2}>
  <Grid item xs={12} md={6}>  {/* Full width on mobile, half on desktop */}
    ...
  </Grid>
</Grid>

// Responsive spacing
sx={{ py: { xs: 2, md: 4 } }}  // 2 on mobile, 4 on desktop
```

---

## State Management Patterns

### Parent state (Day page example)
```tsx
function DayPage() {
  // API data
  const { data: day, isLoading, isError } = useQuery(['day', date], ...);
  const { data: tasks } = useQuery(['tasks'], ...);
  
  // Local UI state
  const [filters, setFilters] = useState<TaskFilters>({...});
  const [selectedEntries, setSelectedEntries] = useState<TimeEntry[]>([]);
  
  // Derived state (computed from filters + tasks)
  const filteredTasks = useMemo(() => 
    tasks.filter(t => matchesFilters(t, filters)), 
    [tasks, filters]
  );
  
  // Event handlers
  const handleAddTask = (task: Task) => { ... };
  const handleUpdateDuration = (taskId: number, minutes: number) => { ... };
  const handleRemoveTask = (taskId: number) => { ... };
  
  return (
    <Page>
      <FiltersBar filters={filters} onFilterChange={setFilters} />
      <TaskPicker tasks={filteredTasks} onAddTask={handleAddTask} />
      <SelectedTasksTable entries={selectedEntries} onUpdateDuration={...} />
    </Page>
  );
}
```

### Props drilling prevention
- Use composition: pass callbacks as props (not Context for MVP)
- Keep state close to where it's used
- Derive state instead of duplicating

---

## Testing Strategy

### Component tests should cover:
- **Rendering**: Component renders without errors
- **Props**: Correct props are displayed
- **Events**: User interactions trigger callbacks
- **States**: Disabled/loading/error states work
- **Edge cases**: Empty lists, long text, invalid input

### Testing patterns (Playwright E2E):
```typescript
// In tests/e2e/day.spec.ts
test('TaskPicker adds task to SelectedTasksTable', async ({ page }) => {
  await page.goto('/day/2025-03-15');
  
  // Click add button on first task
  await page.click('[aria-label="dodaj task"]');
  
  // Verify task appears in selected table
  await expect(page.locator('table tr')).toHaveCount(2); // header + 1 row
});
```

---

## Accessibility Considerations

### ARIA labels
- Buttons have `aria-label` attributes
- Form inputs have labels (visible or aria-label)
- Icon buttons have descriptive aria-label

### Keyboard navigation
- All interactive elements are keyboard accessible
- Tab order is logical
- Enter/Space trigger button actions

### Screen reader support
- Semantic HTML (headings, lists, tables)
- MUI components have built-in accessibility
- Error messages are announced

---

## Performance Optimization

### React optimization patterns
- `useMemo` for expensive computations (filtering large lists)
- `useCallback` for stable callback references (prevent re-renders)
- Conditional rendering (don't render hidden components)

### Avoid over-rendering
```tsx
// Good: memoized filter function
const filteredTasks = useMemo(() => 
  tasks.filter(matchesFilters), 
  [tasks, filters]
);

// Bad: inline filter (runs on every render)
const filteredTasks = tasks.filter(matchesFilters);
```

---

## Do / Don't

### DO
- Use MUI components for consistency
- Keep components focused (single responsibility)
- Pass callbacks as props (not inline functions)
- Use TypeScript interfaces for props
- Handle loading/error states
- Memoize expensive computations
- Use semantic HTML

### DON'T
- Don't put API calls in components (use hooks)
- Don't duplicate state (derive it)
- Don't bypass MUI theming (use `sx` prop)
- Don't hardcode colors/spacing (use theme)
- Don't forget disabled states
- Don't skip TypeScript types
- Don't ignore accessibility

---

## Future Enhancements (not MVP)

- **Component library documentation**: Storybook for visual component docs
- **Unit tests**: Jest + React Testing Library for component tests
- **Custom hooks**: Extract common logic (useTaskFilters, useDayValidation)
- **Error boundaries**: Catch component errors gracefully
- **Skeleton loaders**: Better loading UX than spinners
- **Virtualization**: For very long task lists (react-window)
- **Drag & drop**: Reorder tasks in selected list

---

## Related Documentation

- **Frontend AGENTS.md**: Frontend architecture and patterns
- **Day page AGENTS.md**: Day page specific rules and behavior
- **API documentation**: `backend/timetracker_app/api/AGENTS.md`
- **Design system**: Material-UI documentation

---

## Summary

**Total components**: 9 (4 shared + 5 domain)  
**UI framework**: Material-UI (MUI)  
**State management**: React hooks + TanStack Query  
**Styling**: MUI `sx` prop + theme system  
**Testing**: Playwright E2E tests

These components provide a complete UI toolkit for the TimeTracker MVP, balancing simplicity with reusability.
