# Adaptive Routines App -- Full Specification

## 1. Product Summary

A mobile-first Progressive Web App (PWA) that converts natural-language goals into executable, adaptable calendar routines using AI. The app prioritizes graceful recovery from disruptions over rigid consistency, replacing punitive "streak" mechanics with a positive "Resilience Score" system.

**Core thesis:** The app should feel like a calm, forgiving coach -- not a strict taskmaster. Users should run *to* it when stressed, not away from it.

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Tailwind CSS |
| UI Components | shadcn/ui (ships with Lovable) |
| Icons | lucide-react (stroke-width 1.5) |
| Backend / Auth | Supabase (Postgres, Auth, Row-Level Security) |
| AI Integration | Google Gemini API (gemini-3.1-pro) with JSON mode |
| Deployment | Lovable hosting (Netlify under the hood), PWA-enabled |

---

## 3. Design System

### 3.1 Color Palette

| Role | Light Mode | Tailwind Class | Rationale |
|---|---|---|---|
| Background | Off-white notebook feel | `bg-slate-50` | Calm, neutral canvas |
| Card surface | White | `bg-white` | Floating card aesthetic |
| Primary text | Dark slate | `text-slate-800` | High contrast without harshness |
| Secondary text | Medium grey | `text-slate-500` | De-emphasized metadata |
| Completed (success) | Soft teal | `teal-500` / `teal-100` bg | Nature-inspired, not aggressive green |
| Reshuffled / Adapted | Soft indigo | `indigo-400` / `indigo-100` bg | Signals adaptation, not failure |
| Missed | Muted grey | `slate-300` | Neutral, zero guilt -- no reds |
| Accent / CTA | Warm teal | `teal-600` | Primary action buttons |
| Dark mode background | Deep calm navy | `slate-900` | Optional future enhancement |

**Hard rule:** No harsh reds or punitive colors anywhere in the UI.

### 3.2 Typography

- **Font family:** Inter or Poppins (geometric, rounded, friendly)
- **Hierarchy via weight:**
  - `font-bold text-lg` -- Task contextual topic (primary focus)
  - `font-medium text-slate-500 text-sm` -- Time slots, plan names
  - `font-normal text-slate-400 text-xs` -- Parent plan labels, metadata

### 3.3 Shape Language

- All cards and buttons: `rounded-2xl` or `rounded-3xl` (soft, friendly corners)
- Shadows: `shadow-sm` or `shadow-md` (diffused, floating feel)
- No hard borders; use shadows and background color contrast for separation

### 3.4 Component Patterns

- **Bottom Sheets (Drawers)** over modal pop-ups for all user choices
- **Swipeable cards** for primary task actions
- **Floating Action Buttons** for contextual suggestions (e.g., "Salvage the Day")

---

## 4. Database Schema (Supabase)

### 4.1 `users` Table

| Column | Type | Default | Notes |
|---|---|---|---|
| `id` | UUID | `auth.uid()` | Primary key, linked to Supabase Auth |
| `email` | TEXT | -- | From auth |
| `display_name` | TEXT | -- | Optional |
| `resilience_score` | INTEGER | `0` | Cumulative, never decreases |
| `created_at` | TIMESTAMPTZ | `now()` | Auto |

### 4.2 `plans` Table

| Column | Type | Default | Notes |
|---|---|---|---|
| `id` | UUID | `gen_random_uuid()` | Primary key |
| `user_id` | UUID | -- | FK -> `users.id` |
| `title` | TEXT | -- | e.g., "LeetCode Mastery" |
| `prompt_used` | TEXT | -- | Original user prompt, stored for re-generation |
| `duration_description` | TEXT | -- | e.g., "3 months" -- used when generating monthly breakdowns |
| `total_months` | INTEGER | -- | Total number of months in the plan |
| `months_planned` | INTEGER | `0` | How many months have been broken down into sessions so far |
| `created_at` | TIMESTAMPTZ | `now()` | Auto |

### 4.3 `milestones` Table (High-Level Monthly Plan)

| Column | Type | Default | Notes |
|---|---|---|---|
| `id` | UUID | `gen_random_uuid()` | Primary key |
| `plan_id` | UUID | -- | FK -> `plans.id` ON DELETE CASCADE |
| `user_id` | UUID | -- | FK -> `users.id` (denormalized for RLS) |
| `month_number` | INTEGER | -- | 1, 2, 3... (sequential month within the plan) |
| `title` | TEXT | -- | e.g., "Foundation: Arrays & Strings" |
| `description` | TEXT | -- | e.g., "Build comfort with basic data structures and common patterns" |
| `weekly_themes` | JSONB | -- | Array of 4 weekly theme strings, e.g., `["Arrays basics", "String manipulation", "Hash maps", "Review & practice"]` |
| `is_planned` | BOOLEAN | `false` | True once daily sessions have been generated for this month |
| `created_at` | TIMESTAMPTZ | `now()` | Auto |

### 4.4 `sessions` Table

| Column | Type | Default | Notes |
|---|---|---|---|
| `id` | UUID | `gen_random_uuid()` | Primary key |
| `plan_id` | UUID | -- | FK -> `plans.id` |
| `milestone_id` | UUID | -- | FK -> `milestones.id` (which month this session belongs to) |
| `user_id` | UUID | -- | FK -> `users.id` (denormalized for RLS) |
| `scheduled_time` | TIMESTAMPTZ | -- | When the session is scheduled |
| `duration_minutes` | INTEGER | `30` | Length of session |
| `contextual_topic` | TEXT | -- | e.g., "Two Pointers" |
| `mvr_description` | TEXT | -- | e.g., "Read one solution" |
| `status` | TEXT | `'pending'` | One of: `pending`, `completed`, `completed_mvr`, `reshuffled`, `missed` |
| `original_time` | TIMESTAMPTZ | -- | Stores pre-reshuffle time for history |
| `created_at` | TIMESTAMPTZ | `now()` | Auto |

### 4.5 Row-Level Security

All tables must have RLS enabled. Policy: users can only read/write their own rows (`auth.uid() = user_id`).

---

## 5. Core User Flows

### Flow A: Plan Generation (Two-Tier Architecture)

Plan generation is split into two stages to handle long durations reliably:

**Stage 1: High-Level Plan (runs once when user creates a plan)**

```
User opens "AI Planner" page
  -> Types goal: "I want to do LeetCode for 30 mins every day at 5 PM except Sundays for 3 months"
  -> App calls LLM with the "High-Level Planner" prompt (see Section 7.2)
  -> AI returns a plan title + array of monthly milestones (title, description, weekly themes)
  -> App renders a preview: month cards with themes, not individual sessions
  -> User taps "Looks Good, Lock In Plan"
  -> App inserts the plan + milestones into Supabase
  -> App automatically triggers Stage 2 for Month 1
```

**Stage 2: Monthly Breakdown (runs per month, on demand)**

```
App calls LLM with the "Monthly Breakdown" prompt (see Section 7.3)
  -> Sends: original goal, this month's milestone info, weekly themes, schedule preferences
  -> AI returns JSON array of daily sessions (date, time, topic, MVR) for that month only
  -> App batch-inserts sessions into Supabase `sessions` table
  -> Milestone is marked as is_planned = true, plan.months_planned increments
  -> User sees this month's sessions on their Dashboard timeline
```

**When does Stage 2 run?**
- Automatically for Month 1 right after plan creation
- For subsequent months: user taps "Plan Next Month" button on the Plan Detail page
- The button appears when the current month's sessions are >75% completed or the calendar month is ending

### Flow B: Daily Execution (Dashboard)

```
User opens app (lands on Dashboard)
  -> Sees today's date, Resilience Score in header
  -> Vertical timeline shows sessions ordered by time
  -> Current-time indicator (glowing line) marks "now"
  -> Past sessions are slightly faded
  -> User swipes right on a card OR taps "Complete" -> status = 'completed', +10 points
  -> User swipes left on a card OR taps "Life Happened" -> opens Bottom Sheet
```

### Flow C: The "Life Happened" Reshuffle

```
Bottom Sheet slides up with calming message: "No stress. How do we adjust?"
  -> Option 1: "Downgrade to MVR (5 mins)" -> status = 'completed_mvr', +5 points
  -> Option 2: "Push back 2 hours" -> scheduled_time += 2h, status stays 'pending', +2 points
  -> Option 3: "Skip & Cascade" -> status = 'reshuffled', all subsequent sessions shift forward, +2 points
Bottom Sheet closes, timeline animates to reflect changes
```

### Flow D: Salvage the Day

```
After 6 PM (configurable), if any sessions have status = 'pending':
  -> Floating Action Button appears: "Salvage the Day (15m)"
  -> Tapping it creates a single combined MVR session from all missed tasks
  -> Displays a summary card: "Quick catchup: read one solution + 5 min walk"
  -> Completing it marks all original sessions as 'completed_mvr', +5 points each
```

---

## 6. Screen-by-Screen UI Specification

### Screen 1: Dashboard (Today's Timeline) -- Main View

**Route:** `/` or `/dashboard`

**Layout (top to bottom):**

1. **Top Bar (sticky)**
   - Left: Today's date, formatted friendly (e.g., "Sunday, Mar 8")
   - Right: Resilience Score with subtle glow animation (`text-teal-500 font-bold`)

2. **Timeline Body (scrollable)**
   - Vertical line running down the left margin (`border-l-2 border-slate-200`)
   - Current-time indicator: horizontal glowing teal line across full width
   - Sessions rendered as **Routine Cards** attached to timeline nodes

3. **Routine Card** (the core component)
   - Container: `bg-white rounded-2xl shadow-sm p-4` with swipe support
   - Content hierarchy:
     - Time: `text-sm font-medium text-slate-400` (e.g., "5:00 PM")
     - Topic: `text-lg font-bold text-slate-800` (e.g., "Two Pointers Practice")
     - Plan name: `text-xs text-slate-400` (e.g., "From: LeetCode Mastery")
   - Right side: Two icon buttons
     - Check circle (teal) for Complete
     - Refresh/shuffle (indigo) for Life Happened
   - Status indicators:
     - Completed: teal left border + checkmark overlay + slight opacity
     - Reshuffled: indigo left border + shuffle icon
     - Missed: grey, faded

4. **Salvage Day FAB** (conditional)
   - Appears after 6 PM if pending sessions exist
   - Centered at bottom, floating: `bg-teal-500 text-white rounded-full shadow-lg px-6 py-3`
   - Text: "Salvage the Day (15m)"
   - Subtle pulse animation to draw attention

5. **Bottom Navigation Bar**
   - Three tabs: Today (calendar icon) | Plans (list icon) | AI Planner (sparkles icon)

### Screen 2: AI Planner (Routine Builder)

**Route:** `/planner`

**Layout:**

1. **Chat-style interface** (looks like iMessage / ChatGPT)
   - Messages bubble up from bottom
   - User messages right-aligned, teal background
   - AI responses left-aligned, white background

2. **Input area** (sticky bottom)
   - Text input: `rounded-2xl bg-slate-100 p-4`
   - Placeholder: "Describe your goal and schedule..."
   - Send button: teal circle with arrow icon

3. **Plan Preview Component** (rendered as an AI response bubble after Stage 1 LLM call)
   - Title: Generated plan name
   - Horizontal scrollable **month cards** (not weeks): "Month 1: Foundation", "Month 2: Intermediate", etc.
   - Each month card shows: title + description + 4 weekly theme bullets
   - Duration badge: "3-month plan"
   - Large CTA button: `bg-teal-500 text-white rounded-2xl py-4 w-full font-bold`
   - Text: "Looks Good, Lock In Plan"
   - After tapping: Stage 2 auto-runs for Month 1, then redirects to Dashboard

### Screen 3: Plans Library

**Route:** `/plans`

**Layout:**

1. **Header:** "Your Plans"
2. **Plan cards** (list)
   - Plan title + months planned vs. total months + date created
   - Progress indicator (completed sessions / total generated sessions)
   - Tap to see Plan Detail view
3. **Empty state:** Friendly illustration + "Create your first plan" CTA linking to `/planner`

### Screen 3b: Plan Detail View

**Route:** `/plans/:id`

**Layout:**

1. **Plan header:** Title, original prompt, overall progress
2. **Milestone timeline** (vertical list of monthly milestones):
   - Each milestone card shows: month title, description, weekly themes
   - Status badge:
     - `is_planned = true`: "Active" (teal) -- sessions exist, shows session count + completion rate
     - `is_planned = false` and it's the next month: shows **"Plan Next Month"** button (teal CTA)
     - `is_planned = false` and it's a future month: "Upcoming" (grey)
3. **"Plan Next Month" button:**
   - Triggers Stage 2 LLM call for the next unplanned milestone
   - Shows a loading state: "Generating your sessions..."
   - On success: milestone flips to Active, sessions appear on Dashboard
   - Appears when: the current month's sessions are >75% done OR the calendar date has entered the next month
4. **Session list** (below milestones, filterable by month):
   - Compact Routine Cards showing date, topic, status
   - Grouped by week

### Screen 4: Life Happened Bottom Sheet

**Trigger:** Swipe left on a Routine Card or tap the Life Happened button

**Layout (Drawer / Bottom Sheet):**

1. **Handle bar** at top (standard sheet indicator)
2. **Header text:** "No stress. How do we adjust?" (`text-lg font-bold text-slate-700`)
3. **Subtext:** Shows the session being modified (topic + time)
4. **Three action cards** (stacked vertically):

   **Card A: Downgrade to MVR**
   - Icon: Zap (lightning bolt)
   - Title: "Do the minimum (5 mins)"
   - Subtitle: Shows the MVR text (e.g., "Just read one solution")
   - Badge: "+5 resilience"

   **Card B: Push Back 2 Hours**
   - Icon: Clock
   - Title: "Push back 2 hours"
   - Subtitle: "Reschedule to [new time]"
   - Badge: "+2 resilience"

   **Card C: Skip & Cascade**
   - Icon: ArrowRightCircle
   - Title: "Skip and shift everything"
   - Subtitle: "This moves to the next free slot"
   - Badge: "+2 resilience"

5. **Colors:** All cards `bg-slate-50 rounded-2xl`, no red tones. Calming blues/greys/lavenders.

---

## 7. LLM Integration Specification (Two-Tier Architecture)

### 7.1 API Configuration

- **Provider:** Google Gemini
- **Model:** `gemini-3.1-pro` (latest frontier model, best reasoning and structured output quality)
- **Response format:** JSON mode enabled via `responseMimeType: "application/json"` in generation config
- **API key:** Stored as Supabase Edge Function secret named `GEMINI_API_KEY` (never exposed client-side)

### 7.2 Prompt 1: High-Level Planner (Stage 1)

Called once when the user creates a new plan. Generates the big picture -- monthly milestones and weekly themes -- but NOT individual daily sessions.

```
You are an expert habit coach and long-term learning planner. The user will describe a goal, preferred schedule, and duration.

You must return a JSON object with this structure:

{
  "plan_title": "A short, motivating name for this plan",
  "total_months": 3,
  "milestones": [
    {
      "month_number": 1,
      "title": "A concise name for this month's focus (e.g., 'Foundation: Arrays & Strings')",
      "description": "A 1-2 sentence summary of what the user will achieve this month",
      "weekly_themes": [
        "Week 1 theme (e.g., 'Array fundamentals: traversal, insertion, deletion')",
        "Week 2 theme",
        "Week 3 theme",
        "Week 4 theme"
      ]
    }
  ]
}

Rules:
- Create one milestone per month for the ENTIRE duration
- Each month should build progressively on the previous one
- Weekly themes within each month should have a logical learning arc
- Make milestone titles motivating and specific (not generic like "Month 1")
- The final month should include consolidation/review
- Respect the user's stated skill level if mentioned
```

### 7.3 Prompt 2: Monthly Breakdown (Stage 2)

Called once per month, when the user taps "Plan Next Month" or automatically for Month 1. Generates the actual daily sessions for a single month.

```
You are an expert habit coach. You are generating the DAILY SESSION BREAKDOWN for one specific month of a longer plan.

Context:
- User's original goal: [insert original prompt]
- Schedule: [extracted schedule, e.g., "30 mins daily at 5 PM except Sundays"]
- This is Month [N] of [total]: "[milestone title]"
- Month description: "[milestone description]"
- Weekly themes: [weekly_themes array]
- Start date for this month: [YYYY-MM-DD]

Return a JSON object with this structure:

{
  "sessions": [
    {
      "date": "YYYY-MM-DD",
      "time": "HH:MM",
      "duration_minutes": 30,
      "topic": "A specific, progressive contextual topic for that day. Be concrete and actionable. Don't say 'Run' -- say '3k easy pace run focusing on breathing'. Don't say 'LeetCode' -- say 'Sliding Window: solve 2 medium problems'.",
      "mvr": "A Minimum Viable Routine taking less than 5 minutes that still maintains the habit. Example: 'Put on running shoes and walk around the block' or 'Read one LeetCode solution and understand the approach'."
    }
  ]
}

Rules:
- Generate sessions ONLY for the dates within this month
- Follow the weekly themes provided -- each week's sessions should match its theme
- Make topics progressive WITHIN the month (easier -> harder)
- Each MVR must be genuinely achievable in under 5 minutes
- Respect day exclusions from the schedule
- Vary topics to prevent monotony, even within the same weekly theme
```

### 7.4 Architecture

Both LLM calls happen server-side (Supabase Edge Functions) to protect the API key:

```
STAGE 1 (Plan Creation):
Client -> Edge Function "generate-plan" -> Gemini API -> Parse JSON -> Insert plan + milestones -> Return preview to client

STAGE 2 (Monthly Breakdown):
Client -> Edge Function "generate-month" -> Gemini API -> Parse JSON -> Insert sessions + mark milestone as planned -> Return confirmation to client
```

### 7.5 Gemini API Call Format

Both Edge Functions call the Gemini REST API directly (no SDK needed in Deno):

```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro:generateContent?key=GEMINI_API_KEY

Body:
{
  "contents": [
    { "role": "user", "parts": [{ "text": "<prompt with context>" }] }
  ],
  "generationConfig": {
    "responseMimeType": "application/json",
    "temperature": 0.7
  }
}
```

The response JSON is at `response.candidates[0].content.parts[0].text` -- parse that string as JSON to get the result object.

---

## 8. Gamification: Resilience Score System

### 8.1 Point Rules

| Action | Points | Rationale |
|---|---|---|
| Complete full routine | +10 | Reward for full execution |
| Complete MVR | +5 | Reward for showing up on hard days |
| Reshuffle (push back or cascade) | +2 | Reward for adapting instead of abandoning |
| Missed task | 0 | No punishment. Zero guilt. |

**The score can never decrease.** There are no negative points.

### 8.2 Visual Treatment

- Score displayed in top-right of Dashboard header
- On point gain: subtle glow/pulse animation around the score (teal)
- On reshuffle: indigo glow (reinforces that adapting is positive)
- Future: milestone badges at 100, 500, 1000 points (not in MVP)

---

## 9. Micro-Interactions and Animations

| Interaction | Animation | Implementation |
|---|---|---|
| Complete a task (swipe right) | Card slides off-screen right with teal trail, then reappears faded with checkmark | CSS transition + state change |
| Life Happened (swipe left) | Card reveals indigo background underneath during swipe, opens Bottom Sheet | Swipe library + Drawer component |
| Push Back 2 Hours | Card physically glides down the timeline to its new time position | `transition-all duration-500` on position change |
| Resilience Score increase | Score number counts up with a soft glow pulse | Number animation + box-shadow pulse keyframe |
| Salvage Day button | Subtle breathing/pulse animation | `animate-pulse` (toned down) |
| Plan added to calendar | Session cards cascade onto timeline one by one with stagger | Staggered `transition-delay` |

### Haptic Feedback

Where supported (`navigator.vibrate`), trigger a light 50ms vibration on:
- Task completion
- Reshuffle confirmation
- Plan confirmation ("Add to Calendar")

---

## 10. PWA Requirements

- `manifest.json` with app name, icons, theme color (`#0d9488` teal-600)
- Service worker for offline caching of the dashboard view
- Add-to-homescreen prompt after 2nd visit
- Push notifications for session reminders (future enhancement, not MVP)

---

## 11. MVP Scope vs. Future Enhancements

### MVP (Build This First)

- [x] Dashboard with timeline and Routine Cards
- [x] Complete and Life Happened flows
- [x] Bottom Sheet with 3 reshuffle options
- [x] AI Planner chat with high-level plan preview (Stage 1)
- [x] Monthly breakdown generation with "Plan Next Month" (Stage 2)
- [x] Supabase backend with 4 tables (profiles, plans, milestones, sessions)
- [x] Resilience Score display and point logic
- [x] Salvage the Day FAB
- [x] Basic auth (Supabase email/password or magic link)

### Future Enhancements

- [ ] Push notification reminders ("Time for LeetCode: Two Pointers today")
- [ ] Dark mode (deep navy `slate-900`)
- [ ] Weekly/monthly resilience score charts
- [ ] Milestone badges (100, 500, 1000 points)
- [ ] Calendar export (ICS) / Google Calendar sync
- [ ] Social accountability (share plans with a friend)
- [ ] Multiple plan management with priority ordering
- [ ] AI-powered plan adjustment ("I got sick for a week, rebuild my plan")
