# Crop expansion and Nigeria map UI proposal

**Status:** Documented proposal only; no code or visual assets have been
changed.

**Date:** 2026-09-13

## Plain-language idea

The current farmer can compare the crop forms already listed in the calculator.
Some farmers will grow something else. Add an **Other crop** choice so they
can enter a crop name and still compare it using their own numbers.

Add a simple map of Nigeria to make the location step easier to understand and
more memorable. The first map should be a visual state selector and orientation
aid, not a price heatmap. It must not imply that the app has current prices for
every state.

## Product behavior

### Built-in crops

The existing crop forms remain available with their current labels, units, and
calculator behavior. They continue to be the only crops eligible for the
existing modeled-context suggestions unless a separate mapping is approved.

### Other crop

The farmer chooses **Other crop**, then enters:

| Field | Rule |
| --- | --- |
| Crop name | Required, short plain text; trim whitespace and reject blank or unsafe input |
| Product form | Required, for example fresh fruit, dry grain, tuber, or leaves |
| Yield | Required, farmer-entered tonnes per hectare |
| Selling price | Required, farmer-entered NGN per kg or an explicitly selected unit |
| Costs | The same required non-negative cost fields as built-in crops |
| Price range | Optional low and high values, following the existing range rules |

An Other crop is a normal manual scenario. When its fields are complete, it may
be ranked alongside built-in crops. The calculation must use the farmer's
inputs only; the app must not invent yield, cost, price, unit conversions, or
profit assumptions.

Other crops do not receive an approved snapshot prefill or online price lookup
by default. Adding a crop-specific research mapping requires a separate review
of product form, search terms, units, evidence, and source behavior. Until
then, the research button should either remain unavailable for that crop or
clearly say that the farmer must enter a price manually.

Persist the custom name and form with the local draft. Use a stable sanitized
identifier derived from the name and form, and handle duplicate names without
overwriting another custom scenario. Retired or malformed custom records must
be ignored safely during draft recovery.

## Nigeria map concept

### Recommended first version

Use a local, lightweight SVG map of Nigeria with state regions. Clicking a
state sets the same state value used by the optional research request. The
interface must also provide a normal searchable/selectable state control, so
the map is helpful but never required.

The map should show:

- Nigeria outline and state boundaries;
- the selected state with a strong focus/selected treatment;
- a small label or tooltip for the focused state where space permits;
- a short note such as “Choose your farm state for optional research”; and
- no prices, rankings, or color scale unless a later data visualization gate
  approves them.

The selected state is input context only. It must not alter the offline
calculator result, crop ranking, or stored costs.

### Offline and privacy boundary

- Ship the map asset with the app; do not load Google Maps, Mapbox, tiles, or
  remote JavaScript from the browser.
- Do not send location until the farmer explicitly requests internet research.
- Do not collect GPS coordinates or infer a farmer's location.
- Keep the map usable without network access.
- Include attribution for the boundary source if a third-party SVG or GeoJSON
  is used, and record its license and version before inclusion.

### Accessibility and small screens

- The map is supplementary; the state select/input remains the canonical
  accessible control.
- Every state target needs a keyboard path, visible focus, and an accessible
  name. Do not rely on color alone.
- Provide a text alternative listing the 36 states and FCT.
- Make touch targets large enough for a phone and avoid requiring precision
  tapping on small state regions.
- At narrow widths, place the map below the state control or collapse it into
  an optional “View map” panel.
- Respect reduced-motion preferences and ensure the map does not shift the
  form while loading.

## Visual direction

Keep the current calm field-notebook identity, but give the interface more
character through an editorial agrarian composition:

- a warm paper-toned background with restrained green and harvest-orange
  accents;
- a hand-drawn or screen-printed map treatment with crisp accessible state
  boundaries;
- a stronger “Your field” panel where the state control and map feel like one
  geographic step;
- crop cards with small botanical or harvest marks rather than generic icons;
- clear section transitions and subtle hover/focus motion; and
- the existing small clickable **Created By Deerflow** signature retained in
  the footer.

The design should feel more distinctive without becoming decorative noise. The
calculator remains the primary task, and mobile readability takes priority
over visual effects.

## Proposed implementation waves

1. **Data contract:** define custom-crop IDs, name/form validation, persistence,
   duplicate handling, and manual-only price behavior.
2. **Calculator integration:** add Other crop to selection, editing, ranking,
   printing, reset, and malformed-draft recovery.
3. **Map asset:** select a licensed local SVG/GeoJSON source, record attribution,
   implement accessible state selection, and preserve the text fallback.
4. **Visual refinement:** apply the field-notebook/map composition to the
   existing UI without changing calculator mathematics or research safeguards.
5. **Verification:** test keyboard and mobile flows, offline reload, print
   parity, custom-draft persistence, duplicate names, unsupported research,
   and no automatic price insertion.

## Acceptance criteria for a future implementation gate

- A farmer can add and compare a crop not in the built-in list.
- A custom crop cannot rank until all required fields are complete.
- Custom crops use manual farmer inputs and receive no invented defaults.
- Custom crop names/forms survive reload and do not corrupt existing drafts.
- The map and state control select the same Nigerian state value.
- The map is optional, keyboard accessible, usable offline, and has a text
  alternative.
- No price heatmap or geographic claim is shown.
- The visual changes preserve current warnings, explicit research confirmation,
  offline operation, print parity, and the calculator-only production boundary.
- Existing tests remain green, and new behavior has focused unit and browser
  coverage before deployment.

## Decision needed before coding

Approve or reject these two independent additions:

1. **Custom crop support:** allow an Other crop with manual values only.
2. **Nigeria map:** add a local accessible SVG state selector and visual field
   context without price visualization.

This proposal does not authorize online source expansion, automatic prices,
GPS/location tracking, a third-party map service, or reopening Stage 1.
