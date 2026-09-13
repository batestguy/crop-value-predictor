# Calculator-only moderated pilot session kit — superseded for current Stage 6

> **Deferred future work.** This kit is retained for a future, separately
> authorized human-validation milestone. It is not active Stage 6 evidence and
> its participant thresholds do not apply to the literature-informed gate. See
> [Stage 6](./phases/06-pilot-validation.md) and
> [academic evidence review](./academic-evidence-review.md).

## Scope and handling

Use this kit only for the approved farmer-entered calculator. It must not be
described as a price forecast, a recommendation based on market data, or an
evaluation of Stages 3 or 4. Do not collect names, contact details, exact farm
locations, photographs, recordings, entered figures, or free-text details that
could identify a participant.

The project team assigns a non-identifying session ID such as `F01`–`F10` or
`E01`–`E03` and keeps the participant-level form in project-team controlled
storage. Commit only a summarized aggregate after the team has checked that it
contains no identifying data.

## Facilitator opening and consent

Read verbatim before starting:

> We are testing whether this offline calculator is understandable and useful.
> It uses only the figures entered during this session; it does not predict
> prices or guarantee profit. Taking part is voluntary. We will not record
> your name, phone number, farm location, or the figures you enter. You can
> skip any question or stop at any time. May we continue?

Record only `consent: yes/no`. Stop immediately for `no`; do not create a
session record beyond the anonymous count of declined invitations.

## Preflight checklist

- Confirm the participant is an adult and uses an Android phone or desktop
  browser; record only device class, browser family, and connection condition.
- Use the approved calculator build after one successful online load. Do not
  deploy or publish a new build for the session.
- Confirm the draft is blank. Ask the participant to use invented figures, not
  personal farm or financial information.
- Give no instruction beyond reading each task. Record corrections separately.

## Moderated tasks and observation form

For every task, record one outcome: `independent`, `correction_needed`,
`blocked`, or `not_attempted`. `Independent` means completion without a
facilitator telling the participant which control or value to use.

| ID | Participant task | Evidence to observe | Critical misunderstanding |
|---|---|---|---|
| T1 | Set an area and select two crops. | Two crops remain selected. | Thinks the calculator has already selected a crop for them. |
| T2 | Enter yield, selling point price, and all eight costs for both crops. | Print button becomes available only after completion. | Treats NGN/kg or tonnes/ha as a different unit in a way that changes the decision. |
| T3 | Explain which crop is ranked first and why. | Explains that ranking uses entered scenario profit. | Believes the rank is a guaranteed recommendation or live market prediction. |
| T4 | Add a low/high price range and explain its meaning. | Range is shown as a scenario range. | Treats the range as a promised or statistically validated forecast interval. |
| T5 | Edit the second crop, then print or save the report. | Screen and report reflect the edit. | Report differs from visible scenario without an input change. |
| T6 | Reload, clear the draft, then repeat after networking is disabled. | Expected persistence, reset, and offline behavior occur. | Lost draft or an incomplete scenario produces a result. |

After T6, ask the participant to explain `hectares`, `tonnes/ha`, `NGN/kg`,
and the phrase “scenario, not a promise.” Mark each response `understood`,
`uncertain`, or `misunderstood`; record a brief non-identifying code, not a
verbatim quote. Ask: “How helpful was this for comparing crop scenarios?” and
record a 1–5 rating.

## Session-level safety rules

A critical blocker is any of the following:

- an incomplete scenario receives a result;
- a unit or currency misunderstanding changes the participant's decision;
- the participant believes a result is a forecast or guarantee;
- a saved draft is unexpectedly lost after reload; or
- the offline task fails after the required first online load.

If a critical blocker occurs, stop the task, note its category, and do not
coach the participant to a passing result. Escalate aggregate findings before
running additional sessions if the same blocker occurs twice.

## Aggregate analysis and gate worksheet

Use attempted sessions as the denominator. Report each task separately and do
not replace blocked or not-attempted cases with successes.

| Measure | Calculation | Gate |
|---|---|---|
| Core-task completion | `independent / attempted` for T1, T2, T3, T5, and T6 | At least 80% for every core task |
| Unit/certainty understanding | Count of `misunderstood` responses and critical blockers | No unresolved critical misunderstanding |
| Helpfulness | participants rating 4 or 5 / participants answering | At least 70% |
| Technical reliability | blocked outcomes / attempted, by task and device class | Explain every block; no unresolved critical blocker |

The final repository artifact, if authorized, contains only the sample counts,
percentages, task-level outcomes, device-class totals, blocker categories,
limitations, and the gate decision. It must state that the sample is moderated,
not statistically representative, and calculator-only.

## Calculator release card

Record these fields before the first session in project-team controlled storage:

| Field | Current value |
|---|---|
| Product boundary | Offline, farmer-entered crop-scenario calculator |
| Data use | No automated price source, forecast, account, cloud save, or user-data egress |
| Required inputs | Area, two selected crops, yield, selling point price, and eight costs per crop |
| Output | Ranking by estimated net profit from user-entered scenarios; optional price range is illustrative only |
| Safety copy | “Scenario, not a promise”; not a forecast, confidence interval, or guarantee |
| Known evidence limit | Browser evidence only; no physical Android install/update/offline-recovery evidence |
| Deferred claims | Market prices, national medians, freshness, forecast accuracy, and model performance |

Update this card only with a reviewed release identifier and approved evidence.
