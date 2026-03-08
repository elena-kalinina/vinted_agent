# Adaptive Routines App -- Lovable Implementation Plan

This document contains the exact prompts to paste into Lovable, in order, to iteratively build the Adaptive Routines App. Each step builds on the previous one. Wait for Lovable to finish each step before moving to the next.

---

## Pre-Flight Checklist

Before starting in Lovable:

1. **Create a Supabase project** at [supabase.com](https://supabase.com)
2. **Get a Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey) (free tier is generous)
3. **Create a new Lovable project** -- name it "Adaptive Routines"
4. **Connect Supabase** to Lovable using the Supabase integration (Project URL + anon key)

---

## Step 1: Design System Foundation

**Goal:** Establish the visual language before building any features.

### Prompt 1.1 -- Global Design Tokens

```
Set up a mobile-first React + Tailwind web app with the following design system.
Do NOT build any features yet -- just set up the foundation:

Global Styles:
- Font: Inter (import from Google Fonts)
- Background: bg-slate-50
- Default text: text-slate-800
- All cards: bg-white rounded-2xl shadow-sm
- All buttons: rounded-2xl with generous padding
- No harsh reds or greens anywhere. Success color is teal-500. Adaptation/change color is indigo-400.
- Use lucide-react icons with strokeWidth={1.5} throughout

Create a single placeholder page at "/" that says "Adaptive Routines" centered on screen, styled with these tokens, so I can confirm the design system is working.
```

---

## Step 2: Dashboard Layout and Routine Cards

**Goal:** Build the main screen -- the Today timeline.

### Prompt 2.1 -- Dashboard Structure

```
Build the main Dashboard page at route "/". This is a mobile-first daily timeline view. Layout from top to bottom:

1. TOP BAR (sticky):
   - Left side: Today's date formatted as "Sunday, Mar 8" (use the actual current date)
   - Right side: A "Resilience Score" showing a number (hardcode 42 for now) with a small shield icon from lucide-react. Style it with text-teal-500 font-bold.

2. TIMELINE BODY (scrollable, takes remaining height):
   - A thin vertical line on the left margin (border-l-2 border-slate-200) with small dots at each hour
   - A horizontal "current time" indicator line that spans the full width at the position matching the current time. Make it a thin teal-400 line with a subtle glow (use box-shadow).

3. ROUTINE CARDS attached to the timeline:
   Create 4 sample cards with hardcoded data for testing:
   - Card 1: 9:00 AM, "Morning Breathing Exercise", plan "Mindfulness Journey", status: completed
   - Card 2: 12:00 PM, "Sliding Window Problems", plan "LeetCode Mastery", status: pending
   - Card 3: 3:00 PM, "3k Easy Pace Run", plan "Marathon Prep", status: reshuffled
   - Card 4: 5:00 PM, "Two Pointers Practice", plan "LeetCode Mastery", status: pending

   Each Routine Card design:
   - Container: bg-white rounded-2xl shadow-sm p-4, slight left border color based on status
   - Text hierarchy inside:
     - Time: text-sm font-medium text-slate-400 (e.g., "5:00 PM")
     - Topic: text-lg font-bold text-slate-800 (e.g., "Two Pointers Practice") -- THIS is the primary visual element
     - Plan: text-xs text-slate-400 (e.g., "From: LeetCode Mastery")
   - Two icon buttons on the right side of each card:
     - CheckCircle icon (teal-500) for "Complete"
     - RefreshCw icon (indigo-400) for "Life Happened"
   - Status-based styling:
     - completed: teal-500 left border, content slightly faded, checkmark overlay
     - reshuffled: indigo-400 left border, shuffle icon badge
     - pending: no colored border, full opacity
     - missed: slate-300 everything, most faded

4. BOTTOM NAVIGATION BAR (sticky):
   - Three tabs with lucide-react icons:
     - "Today" (CalendarDays icon) -- active by default, teal-500
     - "Plans" (List icon)
     - "Planner" (Sparkles icon)
   - Style: bg-white border-t border-slate-100, icons centered with small label text below

Make sure the whole page scrolls naturally on mobile. Use padding and spacing that feels spacious, not cramped.
```

---

## Step 3: Supabase Backend

**Goal:** Set up the database and connect the dashboard to real data.

### Prompt 3.1 -- Database Tables

```
Connect this app to Supabase. Create the following database tables using Supabase migrations:

TABLE: profiles
- id: UUID, primary key, references auth.users(id)
- display_name: TEXT, nullable
- resilience_score: INTEGER, default 0
- created_at: TIMESTAMPTZ, default now()

TABLE: plans
- id: UUID, primary key, default gen_random_uuid()
- user_id: UUID, not null, references profiles(id)
- title: TEXT, not null
- prompt_used: TEXT, not null
- duration_description: TEXT, not null (e.g., "3 months")
- total_months: INTEGER, not null
- months_planned: INTEGER, default 0
- created_at: TIMESTAMPTZ, default now()

TABLE: milestones (high-level monthly plan)
- id: UUID, primary key, default gen_random_uuid()
- plan_id: UUID, not null, references plans(id) on delete cascade
- user_id: UUID, not null, references profiles(id)
- month_number: INTEGER, not null
- title: TEXT, not null (e.g., "Foundation: Arrays & Strings")
- description: TEXT, not null
- weekly_themes: JSONB, not null (array of 4 strings)
- is_planned: BOOLEAN, default false
- created_at: TIMESTAMPTZ, default now()

TABLE: sessions
- id: UUID, primary key, default gen_random_uuid()
- plan_id: UUID, not null, references plans(id) on delete cascade
- milestone_id: UUID, not null, references milestones(id) on delete cascade
- user_id: UUID, not null, references profiles(id)
- scheduled_time: TIMESTAMPTZ, not null
- duration_minutes: INTEGER, default 30
- contextual_topic: TEXT, not null
- mvr_description: TEXT, not null
- status: TEXT, default 'pending', check constraint for values: 'pending', 'completed', 'completed_mvr', 'reshuffled', 'missed'
- original_time: TIMESTAMPTZ, nullable
- created_at: TIMESTAMPTZ, default now()

Enable Row Level Security on ALL tables. Policies:
- profiles: Users can read and update only their own row (where id = auth.uid())
- plans: Users can CRUD only their own rows (where user_id = auth.uid())
- milestones: Users can CRUD only their own rows (where user_id = auth.uid())
- sessions: Users can CRUD only their own rows (where user_id = auth.uid())

Also create a database trigger: when a new user signs up (insert into auth.users), automatically create a row in the profiles table with their id and resilience_score = 0.
```

### Prompt 3.2 -- Wire Dashboard to Supabase

```
Now connect the Dashboard to real Supabase data:

1. Add Supabase Auth -- simple email/password sign-up and login. Create a clean login/signup page at "/auth" with the same calm design system (rounded inputs, teal button, no harsh colors). Redirect to "/" after login.

2. Replace the hardcoded Routine Cards on the Dashboard with a real query:
   - Fetch all sessions for the logged-in user where scheduled_time falls on today's date
   - Order by scheduled_time ascending
   - Display them as Routine Cards (same design as before)
   - If no sessions exist for today, show a friendly empty state: "No routines today. Visit the Planner to create one!" with a button linking to "/planner"

3. Fetch the user's resilience_score from the profiles table and display it in the top bar.

4. For now, the Complete and Life Happened buttons don't need to work yet -- we'll add that next.
```

---

## Step 4: Complete and Life Happened Logic

**Goal:** Make the core interaction loop functional.

### Prompt 4.1 -- Complete Button

```
Implement the "Complete" button on each Routine Card:

When a user clicks the CheckCircle (Complete) button on a pending session:
1. Update that session's status to 'completed' in Supabase
2. Add 10 to the user's resilience_score in the profiles table
3. Animate the card: add a teal-500 left border, fade the content slightly, show a checkmark
4. The Resilience Score in the header should animate up (count from old value to new value over 500ms)
5. Trigger a subtle glow/pulse on the score number using a teal box-shadow animation

The button should be disabled for sessions that are already completed, completed_mvr, or missed.
```

### Prompt 4.2 -- Life Happened Bottom Sheet

```
Now build the "Life Happened" flow:

When a user clicks the RefreshCw (Life Happened) button on a pending session, open a Bottom Sheet / Drawer that slides up from the bottom of the screen. Do NOT use a centered modal popup.

Bottom Sheet content:
- A small drag handle at the top
- Header: "No stress. How do we adjust?" in text-lg font-bold text-slate-700
- Subheader showing the session info: "[Topic] at [Time]" in text-sm text-slate-400
- Three option cards stacked vertically, each as a tappable card (bg-slate-50 rounded-2xl p-4):

  Option A -- "Do the Minimum":
  - Icon: Zap from lucide-react (amber-500)
  - Title: "Downgrade to MVR (5 mins)" in font-semibold
  - Subtitle: Show the session's actual mvr_description text from the database
  - Badge: "+5 resilience" in a small teal pill

  Option B -- "Push Back 2 Hours":
  - Icon: Clock from lucide-react (indigo-400)
  - Title: "Push back 2 hours" in font-semibold
  - Subtitle: "Reschedule to [calculated new time]"
  - Badge: "+2 resilience" in a small teal pill

  Option C -- "Skip & Cascade":
  - Icon: ArrowRight from lucide-react (indigo-400)
  - Title: "Skip and shift everything" in font-semibold
  - Subtitle: "This session moves to the next free slot"
  - Badge: "+2 resilience" in a small teal pill

Implement the logic for each option:

Option A (MVR):
- Set session status to 'completed_mvr'
- Add 5 to resilience_score
- Close drawer, update card to show indigo left border

Option B (Push Back):
- Save current scheduled_time into original_time
- Update scheduled_time to +2 hours
- Add 2 to resilience_score
- Close drawer, card should animate/move to its new position in the timeline

Option C (Cascade):
- Set this session's status to 'reshuffled'
- Save current time to original_time
- Find all future pending sessions for the same plan, ordered by scheduled_time
- Push each one forward by the duration of this session
- Add 2 to resilience_score
- Close drawer, refresh timeline

After any option, show the glow animation on the Resilience Score.
```

---

## Step 5: Salvage the Day

**Goal:** Build the end-of-day rescue feature.

### Prompt 5.1 -- Salvage Day FAB

```
Add a "Salvage the Day" floating action button to the Dashboard:

Logic:
- After 6:00 PM local time, check if there are any sessions with status 'pending' for today
- If yes, show a floating button at the bottom center of the screen (above the bottom nav)
- Button style: bg-teal-500 text-white rounded-full shadow-lg px-6 py-3 with a subtle pulse animation
- Button text: "Salvage the Day" with a Sparkles icon

When tapped:
1. Collect all today's pending sessions
2. Show a Bottom Sheet with a summary:
   - Header: "Quick Catch-Up (15 minutes)"
   - List all the MVR descriptions from those pending sessions as a bulleted checklist
   - Example: "- Read one LeetCode solution" / "- Put on shoes, walk one block"
   - A big teal "I Did It" button at the bottom
3. When "I Did It" is tapped:
   - Set all those sessions' status to 'completed_mvr'
   - Add 5 points per session to resilience_score
   - Close the sheet and update the timeline
   - Show the Resilience Score glow animation
```

---

## Step 6: AI Planner (Two-Tier Generation)

**Goal:** Build the AI-powered plan generation. Stage 1 generates a high-level monthly plan. Stage 2 generates daily sessions for one month at a time.

### Prompt 6.1 -- Planner Chat UI (Stage 1: High-Level Plan)

```
Create the AI Planner page at route "/planner" (accessible from the bottom nav "Planner" tab).

Layout -- make it look like a chat interface (similar to ChatGPT or iMessage):

1. Top bar: "AI Planner" title with a Sparkles icon

2. Chat area (scrollable, takes remaining space):
   - Start with a single AI message bubble (left-aligned, bg-white rounded-2xl p-4 shadow-sm):
     "Hi! Tell me about a habit or skill you want to build. Include how often, what time, and for how long. For example: 'I want to practice guitar for 20 minutes every evening at 7 PM for 2 months.'"

3. Input area (sticky bottom):
   - Text input field: bg-slate-100 rounded-2xl p-4, placeholder "Describe your goal and schedule..."
   - Send button: teal-500 circle with Send icon (ArrowUp)

When the user types a message and hits send:
- Show their message as a right-aligned bubble (bg-teal-500 text-white rounded-2xl)
- Show a typing indicator (three animated dots in an AI bubble)
- Call a Supabase Edge Function "generate-plan" that sends the user's prompt to Gemini with this system prompt:

PROMPT:
"You are an expert habit coach and long-term learning planner. The user will describe a goal, preferred schedule, and duration. Return a JSON object with this structure:
{
  \"plan_title\": \"A short motivating name\",
  \"total_months\": 3,
  \"milestones\": [
    {
      \"month_number\": 1,
      \"title\": \"A concise name for this month's focus (e.g., 'Foundation: Arrays & Strings')\",
      \"description\": \"1-2 sentence summary of what the user will achieve this month\",
      \"weekly_themes\": [
        \"Week 1 theme (e.g., 'Array fundamentals: traversal, insertion, deletion')\",
        \"Week 2 theme\",
        \"Week 3 theme\",
        \"Week 4 theme\"
      ]
    }
  ]
}
Rules: Create one milestone per month for the ENTIRE duration. Each month builds progressively. Weekly themes should have a logical learning arc. Make titles motivating and specific. The final month should include consolidation/review.

USER GOAL: [insert user prompt here]"

  - Call Gemini with generationConfig: { responseMimeType: "application/json", temperature: 0.7 }
  - Parse the response from response.candidates[0].content.parts[0].text

After receiving the AI response, render it as a PLAN PREVIEW COMPONENT (not raw text):
- Plan title in text-xl font-bold
- A horizontal scrollable row of MONTH cards (not weeks):
  - Each month card (bg-white rounded-2xl shadow-sm p-4 w-64 flex-shrink-0):
    - "Month 1" label in text-xs text-slate-400
    - Milestone title in font-bold text-slate-800 (e.g., "Foundation: Arrays & Strings")
    - Description in text-sm text-slate-500
    - 4 weekly theme bullets in text-xs text-slate-400
- A duration badge: "3-month plan" in a teal pill
- A large CTA button: bg-teal-500 text-white rounded-2xl py-4 w-full font-bold text-lg
  Text: "Looks Good, Lock In Plan"

When "Looks Good, Lock In Plan" is clicked:
1. Create a new row in the plans table (title, prompt_used, duration_description, total_months, months_planned=0)
2. Batch insert all milestones into the milestones table (linked to the plan, is_planned=false)
3. AUTOMATICALLY trigger Stage 2 (Prompt 6.2 logic) for Month 1's milestone
4. After Month 1 sessions are generated, show success: "Plan locked in! Month 1 is ready on your timeline."
5. Navigate to the Dashboard "/"
```

### Prompt 6.2 -- Monthly Breakdown (Stage 2: Generate Sessions for One Month)

```
Create a reusable function (and a Supabase Edge Function called "generate-month") that generates daily sessions for a single month of a plan.

This function receives:
- The plan's original prompt (from plans.prompt_used)
- The milestone to break down (its title, description, weekly_themes, month_number)
- The plan's schedule preferences (extracted from the original prompt: time, duration, excluded days)
- The start date for this month

It calls Gemini with this prompt:

PROMPT:
"You are an expert habit coach. Generate the DAILY SESSION BREAKDOWN for one specific month of a longer plan.

Context:
- User's original goal: [plan.prompt_used]
- Schedule: [extracted schedule, e.g., '30 mins daily at 5 PM except Sundays']
- This is Month [milestone.month_number] of [plan.total_months]: '[milestone.title]'
- Month description: '[milestone.description]'
- Weekly themes: [milestone.weekly_themes as JSON array]
- Start date: [YYYY-MM-DD]

Return a JSON object:
{
  \"sessions\": [
    {
      \"date\": \"YYYY-MM-DD\",
      \"time\": \"HH:MM\",
      \"duration_minutes\": 30,
      \"topic\": \"Specific progressive topic. Be concrete.\",
      \"mvr\": \"Minimum viable version in under 5 minutes.\"
    }
  ]
}
Rules: Generate sessions ONLY for this month's dates. Follow the weekly themes. Make topics progressive within the month. Each MVR must be achievable in under 5 minutes. Respect day exclusions. Vary topics within the same theme."

  - Call Gemini with generationConfig: { responseMimeType: "application/json", temperature: 0.7 }
  - Parse the response

After receiving sessions:
1. Batch insert all sessions into the sessions table (linked to plan_id and milestone_id)
2. Set the milestone's is_planned = true
3. Increment plans.months_planned by 1
4. Return success to the client

This function will be called:
- Automatically for Month 1 after plan creation (in the "Lock In Plan" flow)
- On demand via the "Plan Next Month" button on the Plan Detail page (built in Step 7)
```

### Prompt 6.3 -- Edge Functions

```
Create TWO Supabase Edge Functions:

FUNCTION 1: "generate-plan" (Stage 1 - High Level)
1. Accepts POST with JSON body: { "prompt": "user's goal description" }
2. Validates authentication (Authorization header JWT)
3. Calls Gemini REST API:
   URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro:generateContent?key=${GEMINI_API_KEY}
   Method: POST
   Headers: { "Content-Type": "application/json" }
   Body: {
     "contents": [{ "role": "user", "parts": [{ "text": "<Stage 1 prompt with user goal>" }] }],
     "generationConfig": { "responseMimeType": "application/json", "temperature": 0.7 }
   }
4. Extracts JSON from: response.candidates[0].content.parts[0].text
5. Returns parsed plan object (title, total_months, milestones array)

FUNCTION 2: "generate-month" (Stage 2 - Monthly Breakdown)
1. Accepts POST with JSON body: { "plan_id": "uuid", "milestone_id": "uuid" }
2. Validates authentication
3. Fetches the plan (prompt_used) and milestone (title, description, weekly_themes) from Supabase
4. Calculates the start date for this month based on month_number and plan creation date
5. Calls Gemini REST API with the Stage 2 prompt (same URL and config as above, different prompt text)
6. Parses the sessions array from the response
7. Batch inserts sessions into the sessions table
8. Updates milestone.is_planned = true and increments plan.months_planned
9. Returns success with session count

Both functions: Store Gemini API key as Supabase secret GEMINI_API_KEY. Handle errors gracefully -- retry once on malformed JSON.
```

---

## Step 7: Plans Library and "Plan Next Month"

**Goal:** Let users view plans, see monthly milestones, and generate the next month's sessions on demand.

### Prompt 7.1 -- Plans List Page

```
Create a Plans page at route "/plans" (accessible from bottom nav "Plans" tab).

Layout:
1. Header: "Your Plans" in text-xl font-bold

2. Plan Cards (vertical list):
   - Fetch all plans for the current user from Supabase, ordered by created_at desc
   - Each card (bg-white rounded-2xl shadow-sm p-4):
     - Plan title in font-bold text-slate-800
     - Created date in text-sm text-slate-400
     - Month progress: "Month 1 of 3 planned" in text-sm text-slate-500
     - Progress bar showing (completed + completed_mvr sessions) / total generated sessions
     - Progress text: "12 / 26 sessions completed"
     - The progress bar should use teal-500 for the filled portion

3. Empty state:
   - If no plans exist, show a friendly message: "No plans yet. Let's create one!"
   - Button linking to "/planner"

4. Tapping a plan card navigates to "/plans/:id" (the Plan Detail view).
```

### Prompt 7.2 -- Plan Detail Page with "Plan Next Month"

```
Create a Plan Detail page at route "/plans/:id".

Layout:
1. HEADER:
   - Back arrow to "/plans"
   - Plan title in text-xl font-bold
   - Subtitle: plan.prompt_used in text-sm text-slate-400 (truncated to 1 line)

2. MILESTONE TIMELINE (vertical list of monthly milestones):
   Fetch all milestones for this plan, ordered by month_number.
   Each milestone renders as a card (bg-white rounded-2xl shadow-sm p-4 mb-4):

   - Top row: "Month [N]" label + status badge on the right:
     - If is_planned = true: "Active" badge in bg-teal-100 text-teal-700 rounded-full px-3 py-1
     - If is_planned = false AND it's the next unplanned month: "Ready to plan" badge in bg-indigo-100 text-indigo-700
     - If is_planned = false AND it's a later month: "Upcoming" badge in bg-slate-100 text-slate-500
   - Title: milestone.title in font-bold text-slate-800
   - Description: milestone.description in text-sm text-slate-500
   - Weekly themes: Show the 4 weekly_themes as a bulleted list in text-xs text-slate-400

   - If is_planned = true:
     - Show session stats below: "22 / 26 sessions completed" with a thin teal progress bar
     - Expandable section: tap to show all sessions for this milestone as compact Routine Cards, grouped by week

   - If is_planned = false AND it's the next unplanned month:
     - Show a prominent "Plan Next Month" button:
       - Style: bg-teal-500 text-white rounded-2xl py-3 w-full font-bold text-center
       - Icon: Sparkles from lucide-react
       - Text: "Plan Month [N]: [milestone.title]"
     - When tapped:
       1. Show loading state on the button: spinner + "Generating your sessions..."
       2. Call the Supabase Edge Function "generate-month" with { plan_id, milestone_id }
       3. On success: refresh the page, milestone flips to "Active", sessions appear
       4. Show a toast: "Month [N] is ready! Check your timeline."

3. BOTTOM AREA:
   - If all months are planned: show a congratulatory message "Full plan generated!"
   - If not: subtle text "Next month unlocks as you progress"
```

---

## Step 8: Polish and Micro-Interactions

**Goal:** Add the finishing touches that make the app feel alive.

### Prompt 8.1 -- Animations and Haptics

```
Add these micro-interactions throughout the app:

1. SWIPE GESTURES on Routine Cards (Dashboard only):
   - Swipe right: triggers the Complete action (same as tapping the check button)
   - Swipe left: opens the Life Happened bottom sheet
   - Show a teal background when swiping right, indigo background when swiping left
   - Use a swipe gesture library compatible with React

2. RESILIENCE SCORE ANIMATION:
   - When the score increases, animate the number counting up over 500ms
   - Add a soft glow pulse (teal box-shadow that fades) around the score on increase
   - When the increase came from a reshuffle, make the glow indigo instead of teal

3. CARD TRANSITIONS:
   - When a session is pushed back 2 hours, animate the card sliding down to its new position (transition-all duration-500 ease-in-out)
   - When a session is completed, add a brief scale-down-then-up "pop" effect

4. HAPTIC FEEDBACK:
   - On task completion, reshuffle confirmation, and plan creation: call navigator.vibrate(50) if available

5. PAGE TRANSITIONS:
   - Use subtle fade transitions when switching between bottom nav tabs
```

### Prompt 8.2 -- PWA Setup

```
Configure this app as a Progressive Web App:

1. Add a manifest.json with:
   - name: "Adaptive Routines"
   - short_name: "Routines"
   - theme_color: "#0d9488" (teal-600)
   - background_color: "#f8fafc" (slate-50)
   - display: "standalone"
   - Appropriate icons (generate simple placeholder icons)

2. Register a basic service worker for offline caching of the app shell

3. Add the appropriate meta tags in index.html for mobile:
   - viewport meta for mobile scaling
   - apple-mobile-web-app-capable
   - theme-color meta tag
```

---

## Step 9: Testing and Seed Data

**Goal:** Make sure everything works end-to-end.

### Prompt 9.1 -- Seed Data and QA

```
Help me test the app by:

1. Creating a seed function (or SQL script) that inserts test data for a logged-in user:
   - 1 plan called "LeetCode Mastery" with prompt "LeetCode 30 mins daily at 5 PM except Sundays for 3 months", total_months=3, months_planned=1
   - 3 milestones:
     - Month 1: "Foundation: Arrays & Strings" (is_planned=true), weekly_themes: ["Array basics", "String manipulation", "Hash maps", "Review"]
     - Month 2: "Intermediate: Trees & Graphs" (is_planned=false), weekly_themes: ["Binary trees", "BST operations", "Graph traversal", "Shortest paths"]
     - Month 3: "Advanced: Dynamic Programming" (is_planned=false), weekly_themes: ["1D DP", "2D DP", "Optimization", "Contest prep"]
   - 7 sessions for this week (linked to Month 1 milestone), each at 5:00 PM, with these topics and statuses:
     - Monday: "Arrays: Two Sum & Contains Duplicate" (completed)
     - Tuesday: "Two Pointers: Valid Palindrome" (completed_mvr)
     - Wednesday: "Sliding Window: Max Subarray" (reshuffled, moved to Thursday 7 PM)
     - Thursday: "Sliding Window: Max Subarray" + "Stack: Valid Parentheses" (pending)
     - Friday: "Binary Search: Search Insert Position" (pending)
     - Saturday: "Linked List: Reverse Linked List" (pending)
   - Each session should have a realistic mvr_description

2. Set the user's resilience_score to 42

This will let me verify:
- Dashboard timeline with status colors and interactions
- Plan Detail page with milestones (1 active, 2 upcoming)
- "Plan Next Month" button appearing on the Month 2 milestone
```

---

## Implementation Order Summary

| Step | What You Build | Key Outcome |
|---|---|---|
| 1 | Design system | Consistent visual language |
| 2 | Dashboard + Routine Cards | Main screen with timeline UI |
| 3 | Supabase tables + Auth + data binding | Real backend (4 tables), login flow |
| 4 | Complete + Life Happened logic | Core interaction loop works |
| 5 | Salvage the Day FAB | End-of-day rescue feature |
| 6 | AI Planner (two-tier) + 2 Edge Functions | High-level plan + monthly breakdown generation |
| 7 | Plans library + Plan Detail + "Plan Next Month" | Browse plans, generate sessions month by month |
| 8 | Animations, swipes, PWA | Polish and native-app feel |
| 9 | Seed data + QA | End-to-end verification |

---

## Tips for Working with Lovable

1. **One prompt at a time.** Wait for Lovable to finish rendering before sending the next prompt. Review the output visually before proceeding.

2. **Fix before moving forward.** If a step produces a bug or visual issue, describe the problem to Lovable and fix it before continuing. Example: "The Routine Cards are too wide on mobile. Please constrain them to max-w-md mx-auto."

3. **Use the Supabase integration early.** Connect Supabase in Step 3 and don't delay it. Data-connected UI is much easier to debug than mocked-up UI.

4. **Keep the Edge Function simple.** If the Edge Function fails to deploy, ask Lovable to show you the function code so you can deploy it manually via the Supabase dashboard. Store your Gemini API key as a Supabase secret named `GEMINI_API_KEY`.

5. **Test on mobile.** After each step, open the Lovable preview on your phone browser to verify the mobile layout. The app is designed mobile-first.
