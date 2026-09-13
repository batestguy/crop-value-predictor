# Stage 6 academic evidence review

**Milestone:** Literature-Informed Calculator Readiness
**Review type:** Rapid scoping review
**Protocol freeze:** 2026-09-09
**Reporting frame:** PRISMA 2020, with JBI scoping-review guidance
**Decision status:** Approved — literature-informed readiness (user decision 2026-09-09)

## Decision boundary

This review establishes literature-informed design requirements, adoption risks,
accessibility checks, and a future evaluation method for the calculator. It does
not establish that this calculator is understandable, helpful, safe, or usable
by Nigerian farmers. No included source supplies a denominator for this product,
and no literature finding is treated as evidence of Nigerian farmer comprehension,
usefulness, completion rate, offline recovery, or real-device performance.

The participant protocol and session kit remain retained as deferred human-
validation materials. They are not active Stage 6 gate evidence.

## Review question and scope

**Question:** What design requirements, adoption risks, literacy/accessibility
considerations, and evaluation methods are supported by research for an
offline-first crop-scenario calculator intended for Nigerian and comparable
smallholder-farming contexts?

The scope covered four evidence areas:

1. Nigerian and Sub-Saharan African agricultural technology adoption;
2. LMIC digital literacy, low literacy, offline operation, infrastructure, and
   access;
3. usability inspection, heuristic evaluation, cognitive walkthrough,
   accessibility, and decision-support evaluation methods; and
4. systematic-review, quality-appraisal, reporting, and official
   evidence-synthesis guidance.

The unit of evidence is a publication or authoritative guidance document. The
unit of product judgment is a calculator requirement or test, not a participant
outcome.

## Sources and search dates

Searches were run and frozen on **2026-09-09** in PubMed, Europe PMC, OpenAlex,
and DOAJ. Reference-list chasing was limited to the included papers and the
official PRISMA, JBI, WHO, W3C, and ISO pages. The search was English-language
only because the repository does not yet have a reviewed multilingual search
workflow; language and database coverage are limitations.

The source counts below are the screening record for this rapid review:

| Source or step | Records |
|---|---:|
| PubMed | 86 |
| Europe PMC | 34 |
| OpenAlex | 97 |
| DOAJ | 21 |
| Official guidance and reference-list candidates | 8 |
| Raw records before deduplication | 246 |
| Unique records after DOI/title deduplication | 177 |
| Title/abstract records screened | 177 |
| Excluded at title/abstract | 138 |
| Reports sought for full text | 39 |
| Full texts unavailable or not retrievable | 7 |
| Full texts assessed | 32 |
| Full-text exclusions | 12 |
| Included sources in the matrix | 20 |

The counts are intentionally reported as a rapid-review audit trail rather than
as a claim of exhaustive retrieval. The 20 included sources meet the target of
at least 12 accessible full-text sources and at least three sources in each
evidence area.

## Exact search strings

The following strings were used as the conceptual strings. Database-specific
field syntax was applied only where required by the host interface; no date
filter was applied to the agricultural searches, and the digital-intervention
searches were limited to 2000–2026.

### Agriculture and Nigeria/SSA

    (Nigeria OR "sub-Saharan Africa" OR Africa) AND (farmer* OR smallholder* OR agriculture) AND (mobile OR smartphone OR app OR ICT OR "digital agriculture") AND (adoption OR usability OR literacy OR access OR "decision support")

### LMIC literacy, offline, and access

    ("low- and middle-income" OR LMIC OR "resource-limited") AND ("digital literacy" OR "health literacy" OR eHealth OR "digital divide" OR offline OR connectivity OR accessibility) AND (mobile OR smartphone OR web OR application OR intervention)

### Usability and evaluation methods

    (usability OR "heuristic evaluation" OR "cognitive walkthrough" OR accessibility OR "decision support" OR "user-centered") AND (calculator OR application OR app OR "digital intervention" OR software) AND (evaluation OR testing OR method* OR requirement*)

### Evidence synthesis and reporting

    ("scoping review" OR "systematic review" OR PRISMA OR JBI OR MMAT OR "quality appraisal" OR "monitoring and evaluating") AND (digital OR mobile OR health OR agriculture OR intervention OR usability)

## Eligibility and screening

### Inclusion criteria

- Peer-reviewed research, systematic/scoping reviews, or official standards and
  guidance with a stable DOI or authoritative URL.
- Evidence about agricultural digital tools in Nigeria/SSA; digital literacy,
  low-literacy design, offline/connectivity, or access in LMIC/resource-limited
  settings; usability/evaluation methods; or evidence-synthesis practice.
- A population, technology, design method, infrastructure context, or reporting
  practice that could inform this calculator's requirements or its future
  evaluation.
- English full text or a stable authoritative record with a sufficiently
  detailed abstract for a bounded contextual judgment.

### Exclusion criteria

- Pure agronomic or price/forecasting studies without a digital-use or
  evaluation implication.
- Product marketing, app-store descriptions, opinion pieces, and unsupported
  claims of adoption or impact.
- Studies that only describe high-income clinical settings with no transferable
  design or evaluation lesson.
- Duplicate reports, inaccessible records with no stable bibliographic record,
  and sources whose claims could not be separated from speculation.

### Screening record

Pass 1 screened titles and abstracts against the criteria above and recorded one
primary reason for exclusion. Pass 2 independently re-read the 32 full-text
records selected for retrieval, checked the 20 included citations against their
DOI/URL landing pages, and rechecked each extracted claim against the source
abstract or full text. Disagreements were resolved by retaining the narrower
claim and downgrading the evidence tier where transferability was uncertain.
This second pass is an internal audit pass, not a substitute for an external
reviewer or participant validation.

## Quality appraisal and evidence tiers

The review uses the 2018 Mixed Methods Appraisal Tool (MMAT) as a design-aware
quality check for empirical and review studies. For standards and guidance, the
check is whether the issuing body, scope, version, and intended use are clear.
The appraisal is not converted into a pooled score: heterogeneous designs,
outcomes, and populations make a numerical meta-analysis inappropriate here.

Each matrix row also receives a transfer tier:

- **direct:** Nigerian or SSA agricultural evidence closely matches the product
  context, but still does not validate this calculator;
- **transferable:** a similar LMIC, low-literacy, offline, or digital-evaluation
  setting supports a bounded design inference;
- **contextual:** methods or standards inform how to design, report, or test the
  product rather than what Nigerian users will do; and
- **insufficient:** useful as a prompt or inspection aid, but not sufficient to
  support a product or population claim.

The extraction matrix is [academic-evidence-matrix.csv](./academic-evidence-matrix.csv).

## Thematic synthesis

### 1. Adoption depends on exposure and enabling conditions

The Nigeria/SSA literature associates agricultural technology use with exposure,
education, skills, network access, charging/electricity, affordability, and
perceived usefulness. These are adoption conditions, not proof that a particular
interface is understood or beneficial. The immediate requirement is therefore
to keep the calculator anonymous, lightweight, and explicit about what each
input and result means, while leaving adoption and usefulness unresolved until
direct human research is authorized.

### 2. Low-literacy and digital-divide risks require inclusive defaults

The LMIC literature supports simple language, visible explanations, multimodal
support where available, human or peer support in future evaluation, and design
that does not assume stable connectivity, electricity, high literacy, or a
recent device. It does not support a claim that English-only copy works for
Nigerian farmers. Translation and comprehension remain deferred risks.

### 3. Inspection methods can find defects; they cannot stand in for users

ISO 9241-11, heuristic inspection, cognitive walkthroughs, WCAG, and reporting
guidance provide structured checks for task flow, recognition, error prevention,
accessibility, and transparent evaluation. They can justify automated tests and
review checklists. They cannot establish comprehension, confidence in units,
interpretation of rankings, or real-world usefulness.

### 4. Evaluation must report the product, context, and denominator

PRISMA/JBI, MMAT, WHO monitoring and evaluation guidance, mERA, and the public-
end-user evaluation review support explicit methods, context, implementation
details, user involvement, outcomes, limitations, and reproducible reporting.
The project therefore replaces participant thresholds in this milestone with a
literature traceability gate and retains participant validation as future work.

## Concern-to-requirement and test map

| Calculator concern | Evidence-informed decision | Current test, warning, or unresolved limitation |
|---|---|---|
| Units (hectares, t/ha, NGN/kg, NGN/ha) | Keep unit labels adjacent to every field and result; never rely on memory or a generic glossary. | Existing validation and browser tests cover required units and invalid values. Farmer interpretation remains unresolved and requires future task testing. |
| Input validation | Prevent incomplete or non-finite values from producing rankings; show a plain-language correction. | Existing calculator tests and browser flows cover incomplete, invalid, and recoverable inputs. Error comprehension is not proven. |
| Ranking interpretation | Present ranking as arithmetic for the entered scenario, not a recommendation, promise, or forecast. | Existing result copy and snapshot checks preserve calculator-only semantics. The meaning users assign to “best” remains unresolved. |
| Price-range meaning | Label low/high prices as an entered scenario range, not a confidence or forecast interval. | Existing UI/report assertions check the disclaimer. Understanding of ranges requires participant validation. |
| Offline persistence | Preserve a local draft, recover safely after reload, and fail closed when storage is blocked or malformed. | Existing persistence tests and offline E2E coverage pass. Physical Android recovery is still absent. |
| Low bandwidth | Keep the static bundle and calculation local; do not require a network request after the first successful load. | Existing no-egress and throttled-browser evidence pass. Coverage is browser-based, not field-based. |
| Accessibility | Use visible labels, keyboard access, semantic controls, readable contrast, and WCAG-informed checks. | Existing axe, keyboard, responsive, and print/report tests pass the recorded browser scope. Assistive-technology and local-context testing remain open. |
| Language and literacy | Use plain English now, keep copy externalized, and defer Pidgin/Hausa/Yoruba/Igbo releases until translation and user review. | Locale-ready architecture and copy review are required; no language is represented as farmer-validated. |
| Evaluation claims | Separate literature-informed readiness, browser evidence, physical-device evidence, and participant evidence. | This review and its two audit passes are the Stage 6 gate evidence. Participant validation remains absent. |

## Limitations and unresolved risks

- The search is rapid, English-language, and limited to four bibliographic
  platforms plus targeted authoritative guidance.
- The evidence is heterogeneous and often concerns health rather than
  agriculture; transfer is bounded to interface, access, and evaluation risks.
- Nigerian agricultural studies primarily address adoption or exposure, not
  comprehension of this calculator's units, rankings, or price ranges.
- No source supplies a defensible participant denominator for this product.
- No source proves real-device Android installation, update behavior, offline
  recovery, or low-bandwidth performance for this repository's build.
- No meta-analysis was performed because the measures and interventions are not
  genuinely comparable.
- The internal second review pass improves traceability but is not independent
  external peer review. A future evidence refresh should add a second human
  reviewer and update the search log.

## Stage 6 gate decision

The protocol, search log, screening record, extraction matrix, references,
quality/context judgments, two review passes, requirement map, warnings, and
deferred risks are complete. Major product claims are labelled as direct,
transferable, contextual, or insufficient; no literature finding is represented
as proof of Nigerian farmer comprehension, usefulness, completion, offline
recovery, or real-device performance.

**Decision:** Approved — literature-informed readiness, recorded after the
user's explicit gate decision on 2026-09-09. Participant validation remains
absent, and the stage must never be labelled farmer-validated.

## References

The full extraction is maintained in the matrix. The highest-use sources for the
decision boundary are:

- [Kolapo & Didunyemi (2024), agricultural smartphone apps in Southwest Nigeria](https://doi.org/10.1186/s40066-024-00485-1)
- [Ayim et al. (2022), ICT adoption in African agriculture](https://doi.org/10.1186/s40066-022-00364-7)
- [Cheng et al. (2020), eHealth literacy and socially disadvantaged groups](https://doi.org/10.2196/18476)
- [Hamilton et al. (2025), digital-divide design and deployment](https://doi.org/10.3310/GJHG1331)
- [Pavão & Werneck (2021), health literacy in LMICs](https://doi.org/10.1590/1413-81232021269.05782020)
- [Weirauch et al. (2024), public end-user evaluation methods](https://doi.org/10.2196/55714)
- [PRISMA 2020](https://doi.org/10.1136/bmj.n71)
- [JBI Manual for Evidence Synthesis](https://jbi-global.atlassian.net/wiki/spaces/MANUAL)
- [WHO monitoring and evaluation guide](https://www.who.int/publications/i/item/9789241511766)
