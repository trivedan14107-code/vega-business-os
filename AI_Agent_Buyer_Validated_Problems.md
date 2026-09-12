# Buyer-Validated AI Agent Problems

## Executive conclusion

The strongest opportunity is a **specialty-care exception closure agent** that moves a patient from referral through prior authorization to a booked appointment.

The agent would read incoming referrals, gather missing records, determine payer requirements, prepare and submit authorization requests, monitor portals and faxes, call the insurer when necessary, organize peer-to-peer review, handle non-clinical appeal steps, book the patient, and record every action in the EHR. Humans retain clinical decisions and approve uncertain cases.

This is a real, high-frequency workflow with active buyers. The American Medical Association reports approximately 40 prior authorizations per physician per week and 13 hours of weekly work. Forty percent of practices employ staff dedicated exclusively to the process.[^1] CMS is organizing 29 early-adopter organizations ahead of 2027 electronic-prior-authorization requirements.[^2] A currently published SUNY Upstate Medical University procurement seeks a cloud-based prior-authorization and 340B AI solution, with proposals due September 15, 2026.[^3]

The gap is not another form generator or dashboard. Existing products automate the clean cases. The remaining opportunity is to complete the messy exceptions that still require calls, faxes, missing-document searches, payer-specific rules, appeals, scheduling and cross-team follow-up.

## Scoring method

Each opportunity receives six scores from 1 to 5. The final score averages pain, frequency, budget, buyer readiness, agent fit and competitive whitespace. Competitive whitespace is the inverse of crowding; a market full of strong vendors receives a low whitespace score.

| Rank | AI-agent problem | Pain | Frequency | Budget | Buyer readiness | Agent fit | Whitespace | Opportunity |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Specialty referral-to-authorization closure | 5.0 | 5.0 | 5.0 | 5.0 | 4.5 | 2.0 | **4.4/5** |
| 2 | B2B receivables exception resolution | 5.0 | 5.0 | 4.0 | 5.0 | 5.0 | 2.0 | **4.3/5** |
| 3 | Property-maintenance resolution | 5.0 | 5.0 | 4.0 | 5.0 | 4.0 | 2.0 | **4.2/5** |
| 4 | Freight exception-to-cash | 5.0 | 5.0 | 4.5 | 5.0 | 4.0 | 1.0 | **4.1/5** |
| 5 | AML investigation-package preparation | 5.0 | 5.0 | 5.0 | 4.0 | 4.0 | 2.0 | **4.1/5** |
| 6 | Industrial maintenance alert-to-action | 5.0 | 5.0 | 5.0 | 4.0 | 3.0 | 2.0 | **4.0/5** |
| 7 | Accounts-payable exception resolution | 4.0 | 5.0 | 4.0 | 5.0 | 5.0 | 1.0 | **4.0/5** |
| 8 | Insurance-claim evidence coordination | 5.0 | 5.0 | 5.0 | 4.0 | 4.0 | 1.0 | **4.0/5** |

## 1. Specialty referral-to-authorization closure agent

### Workflow

Referral received by fax, email or portal → patient and insurance verified → missing records requested → payer rules identified → chart evidence assembled → request submitted → status monitored → requests for information resolved → peer-to-peer review prepared → outcome recorded → appointment booked → patient and referring office updated.

### Buyers already acting

- **SUNY Upstate Medical University** is seeking an AI solution for pharmacy, medical, specialty and infusion authorizations, including clinical-data retrieval, scanned-document extraction, form completion and staffing reduction.[^3]
- **Texas Health Resources** selected Humata and deployed prior-authorization automation across imaging, cardiovascular services and interventional radiology.[^4]
- **Allegheny Health Network** uses Humata for more than 200,000 annual authorizations.[^5]
- **Cleveland Clinic** is deploying Luminai first for external fax referrals, a workflow it describes as manually sorted, prioritized and entered into the EHR.[^6]
- **Wellstar Health System** co-developed Flare Health's ReferAI for converting faxed referrals into ready-to-schedule Epic orders.[^7]
- **CMS early adopters** include Cleveland Clinic, Providence, Ochsner, Epic, Oracle, Aetna, Cigna, Humana, Elevance and UnitedHealthcare.[^2]

### What current companies have solved

Humata/R1, Cohere Health, CoverMyMeds, Infinx, Waystar and Availity address authorization requirements, document collection, submission, status and some touchless approvals. Luminai, Tennr, Flare Health, ReferralMD and Ema address referral intake, OCR, classification and routing.

### Remaining gap

- Resolve the last 10–20% of cases that fall out of automated workflows.
- Work across payer portals, EHRs, phone calls, fax and email.
- Detect conflicting payer rules and missing or stale chart evidence.
- Prepare human peer-to-peer review without making the clinical decision.
- Connect authorization completion to an actual scheduled appointment.
- Preserve a cited, replayable audit timeline.
- Measure completed care and captured revenue, not forms submitted.

### Recent public social reviews

These posts are anecdotal and identities are not independently verified.

- A physician described spending an entire day on a denied CT authorization and being told to restart the process with a different organization. The June 25, 2026 post received more than 1,200 votes.[^8]
- A small supplier reported 45 minutes of work per authorization and said it stopped accepting new Medicare patients for affected codes because the economics no longer worked.[^9]
- A billing professional said their health system was considering paying a vendor a substantial premium to counter automated denials.[^10]
- A July 2026 health-technology discussion captured a central objection: many “AI denial” products may simply create a new queue that staff must verify manually.[^11]
- A rural specialist reported approximately 2,000 unscheduled referrals and a three-to-six-month wait, showing that extraction alone does not close the workflow.[^12]

### Recommendation

Start with one specialty such as diagnostic imaging, oncology, orthopedics or infusion. Sell to a 20–200-provider specialty group, imaging network or ambulatory surgery group. Charge for completed authorizations, booked cases or recovered revenue. The large health systems validate the market but are poor first customers because procurement and integration are slow.

## 2. B2B accounts-receivable exception agent

### Workflow

Prioritize overdue invoice → find correct customer contact → resend invoice or missing document → read reply → retrieve missing PO → investigate short payment or deduction → match remittance → record promise to pay → route a true dispute → update ERP and audit log.

### Buyers already acting

Microsoft says internal collections agents unlocked hundreds of thousands of staff hours annually, reduced call preparation by 40%, doubled automatic cash application and accelerated inquiry resolution 2.5 times.[^13]

### Existing solutions

HighRadius, Billtrust, BlackLine, Sidetrade, Tesorio, Upflow, Monto and other order-to-cash platforms already provide prioritization, standard reminders, dashboards and clean-payment matching.

### Gap

The expensive work begins when a customer short-pays, withholds a purchase order, uses a proprietary AP portal, disputes a line item or sends an unclear email. A useful agent must close those cases across ERP, CRM, bank files, email and portals. “Better reminder emails” are not enough.

### Public social review

A March 2026 ERP discussion said payment matching, malformed replies, dirty customer data, short-pay disputes and upstream PO failures defeat many existing products. Practitioners warned that weak tools merely create another queue to monitor.[^14]

### Recommendation

Strong horizontal opportunity. Start B2B-only with missing PO requests, remittance matching, short-pay classification and customer-portal status checks. Human approval should remain mandatory for credits, write-offs and payment-term changes.

## 3. Property-maintenance resolution agent

### Workflow

Receive resident request → gather photos and diagnose → determine urgency → choose approved vendor → schedule access → chase vendor → update resident → verify completion → validate invoice and evidence → close work order.

### Buyers already acting

- **Action Property Management** uses Zendesk AI across more than 300 communities and reports large response-time and automation improvements.[^15]
- **Asset Living** partnered with EliseAI across a 450,000-unit portfolio, including MaintenanceAI.[^16]
- **AppFolio** reports that 96% of customers used at least one Realm AI capability in 2025 and offers a Maintenance Performer.[^17]

### Solved and gap

Chat intake, FAQs, basic triage, resident messages and work-order creation are widely available. The unresolved work begins after dispatch: vendor chasing, rescheduling, entry coordination, insurance validation, estimate approval, before/after evidence, resident updates, invoice matching and confirmation that the repair actually worked.

### Public social reviews

- A maintenance coordinator described beginning a day with 14 untriaged requests and uncertainty about whether vendor insurance was current.[^18]
- A manager responsible for 659 units said existing property software lacked adequate reminders and task management; the discussion also rejected a competing product priced at $6 per unit monthly.[^19]
- A five-year practitioner described the post-dispatch follow-up loop as the largest headache for growing management firms.[^20]

### Recommendation

Build a “maintenance closer,” not an AI receptionist. Target managers of 500–10,000 units and begin with non-emergency vendor follow-through. Pricing can be per unit or successfully resolved work order.

## 4. Freight exception-to-cash agent

### Workflow

Read rate confirmation → schedule dock → monitor driver and arrival → identify detention/accessorial event → collect ELD timestamps, BOL, photos and messages → apply contract notice rules → submit invoice/claim → chase approval → reconcile payment.

### Buyers already acting

DHL is deploying HappyRobot agents for appointment scheduling, driver follow-up, warehouse coordination and invoice follow-up across large email and voice volumes.[^21] United States Cold Storage deployed FourKites scheduling automation across 38 facilities.[^22]

### Solved and gap

Appointment scheduling, routine status calls, ETA messages, document extraction and simple invoice audits are increasingly solved. The remaining gap is turning a live exception into collected cash. Evidence is scattered across telematics, texts, email, images, TMS records, facility policies and rate confirmations.

### Public social reviews

Recent trucker and broker discussions describe abandoning valid detention charges, 30-day disputes, inconsistent policies and having to assemble timestamps and documentation immediately.[^23]

### Recommendation

Target 50–500-truck carriers and mid-sized 3PLs. Begin with detention and accessorial recovery, charging a portion of verified recovered revenue. Competition is intense, so the product must own recovery rather than another scheduling interaction.

## 5. AML investigation-package agent

### Workflow

Accept monitoring alert → retrieve KYC, ownership, account history and related alerts → build transaction and entity graph → detect missing or conflicting records → map facts to policy → draft a cited case packet → send to human investigator.

### Buyers already acting

Amalgamated Bank is a design partner with FIS and Anthropic for an AML agent that assembles and evaluates evidence while leaving suspicious-activity-report decisions with humans.[^24] FIS identifies BMO as another initial institution and planned broader availability in the second half of 2026.[^25]

### Solved and gap

NICE Actimize, Verafin, Feedzai, Unit21, Fenergo, Hummingbird, Greenlite, FIS and others handle detection, queues, screening, enrichment and narrative drafting. The gap is reliable evidence assembly across blurry documents, registries and multilayer ownership, with traceable policy justification.

### Public social review

A January 2026 banking discussion said agent demonstrations often fail on poor documents, conflicting registry data and four-layer ownership structures. The central warning was that “fast and wrong” creates audit debt.[^26]

### Recommendation

Pursue only with financial-crime expertise and a bank design partner. Begin with evidence gathering and quality assurance; do not automatically file or close cases.

## 6. Industrial-maintenance alert-to-action agent

### Workflow

Receive machine alert → identify asset and safety context → retrieve manual and repair history → prepare diagnostics → obtain supervisor approval → create work order → reserve parts and technician → guide repair → capture voice/photos → update CMMS and preventive plan.

### Buyers already acting

Autowash reports using MaintainX AI across 26 locations, with a 74% reduction in mean time to repair and more than $3 million in avoided downtime.[^27] Siemens has launched maintenance copilots and reports adoption by thyssenkrupp Automation Engineering.[^28]

### Solved and gap

Sensors, alerts, predictive warnings, CMMS work orders and troubleshooting search already exist. The broken handoff is between detecting the fault and getting safe work approved, scheduled, completed, documented and incorporated into future maintenance.

### Public social reviews

A September 9, 2026 technician reported that a known issue waited for CMMS approval, turning a 15-minute repair into three hours; the poster said similar incidents had occurred more than five times in two months.[^29] Other practitioners described technicians failing to document repairs and inaccurate CMMS data driving teams back to private notes and paper.[^30]

### Recommendation

Pilot only. Build a voice-first execution assistant for one machine family or maintenance workflow. It may prepare and document work but should not directly control equipment.

## Immediate build recommendation

### Imaging authorization and scheduling agent

The minimum product should handle a narrow sequence:

1. Watch one referral inbox or fax queue.
2. Extract patient, procedure, diagnosis and referring-provider data.
3. Verify that the required records and recent labs are present.
4. Check payer-specific authorization requirements.
5. Prepare the submission with cited chart evidence.
6. Track the request and identify requests for additional information.
7. Draft the exact call or response needed, escalating clinical uncertainty.
8. When approved, trigger scheduling and notify the patient and referring office.
9. Maintain a complete, timestamped audit trail.

The first pilot should prove four outcomes: staff minutes removed per case, first-pass completeness, days from referral to decision, and percentage of approved cases that become booked appointments.

### Kill criteria

Interview 15 imaging centers or specialty groups. Stop or change direction if:

- fewer than five report at least one full-time-equivalent devoted to referral/authorization follow-up;
- fewer than five can quantify lost or delayed cases;
- fewer than three will provide a de-identified sample workflow and payer mix;
- no organization will sign a paid pilot tied to completed cases;
- the product cannot achieve reliable source citation and human escalation on retrospective cases.

## What not to build

- Generic AI receptionist
- Generic prior-authorization letter writer
- Fax OCR product
- Generic accounts-payable invoice scanner
- Generic procurement chatbot
- Fully autonomous insurance adjuster
- Autonomous industrial-equipment controller
- Another dashboard that identifies work but does not complete it

## Sources

[^1]: American Medical Association, “[Latest prior auth survey shows promised reform remains elusive](https://www.ama-assn.org/about/leadership/latest-prior-auth-survey-shows-promised-reform-remains-elusive),” June 4, 2026.
[^2]: Centers for Medicare & Medicaid Services, “[CMS Announces Early Adopters to Advance Solutions for Electronic Prior Authorization](https://www.cms.gov/newsroom/press-releases/cms-announces-early-adopters-advance-solutions-electronic-prior-authorization-accelerating-momentum),” May 13, 2026.
[^3]: SUNY Upstate Medical University procurement summary, “[Cloud-Based Prior Authorization and 340B AI Solution](https://usesettle.com/rfp-hunter/cloud-based-prior-authorization-and-340b-ai-solution-2328954),” August 27, 2026.
[^4]: Humata Health, “[Texas Health Resources Prior Authorization Automation](https://www.humatahealth.com/resources/texas-health-resources-prior-authorization-automation),” May 12, 2026.
[^5]: Humata Health, “[Allegheny and Humata 200K PA Partnership](https://www.humatahealth.com/blog/allegheny-and-humata-200k-pa-partnership),” 2026.
[^6]: Cleveland Clinic, “[Cleveland Clinic Partners with Luminai](https://newsroom.clevelandclinic.org/2026/09/09/cleveland-clinic-partners-with-luminai-to-transform-health-system-operations),” September 9, 2026.
[^7]: Flare Health, “[Patient Access and ReferAI](https://flarehealth.com/solutions/patient-access/),” accessed September 2026.
[^8]: Reddit r/medicine, “[Prior authorization; or How I Became Radicalized](https://www.reddit.com/r/medicine/comments/1ufj0dp/prior_authorization_or_how_i_became_radicalized/),” June 25, 2026.
[^9]: Reddit r/healthcare, “[Is anyone else's prior auth workload getting worse?](https://www.reddit.com/r/healthcare/comments/1sy0afs/is_anyone_elses_prior_auth_workload_getting_worse/),” April 28, 2026.
[^10]: Reddit r/dataisbeautiful, “[Prior authorization consumes more clinician FTEs](https://www.reddit.com/r/dataisbeautiful/comments/1vti85x/oc_prior_authorization_consumes_more_clinician/),” August 20, 2026.
[^11]: Reddit r/HealthTech, “[What's the actual deal with AI denial management tools?](https://www.reddit.com/r/HealthTech/comments/1v01ek6/ok_whats_the_actual_deal_with_ai_denial/),” July 18, 2026.
[^12]: Reddit r/medicine, “[Drowning in referrals](https://www.reddit.com/r/medicine/comments/1v5g5zl/drowning_in_referrals/),” July 24, 2026.
[^13]: Microsoft, “[Streamlining finance cash collection at Microsoft with AI](https://www.microsoft.com/insidetrack/blog/streamlining-finance-cash-collection-at-microsoft-with-ai/),” June 4, 2026.
[^14]: Reddit r/ERP, “[Manual collections is crushing my AR team](https://www.reddit.com/r/ERP/comments/1rvgmfs/manual_collections_is_crushing_my_ar_team_are_ai/),” March 16, 2026.
[^15]: Zendesk, “[Action Property Management customer story](https://www.zendesk.com/customer/action-property-management/),” accessed September 2026.
[^16]: EliseAI, “[Asset Living partners with EliseAI](https://eliseai.com/blog/asset-living-partners-with-eliseai),” accessed September 2026.
[^17]: AppFolio, “[Investor Meeting Materials](https://www.sec.gov/Archives/edgar/data/1433195/000143319525000145/appfolioinvestormeeting2.htm),” 2025.
[^18]: Reddit r/PropertyManagement, “[Four years as a maintenance coordinator](https://www.reddit.com/r/PropertyManagement/comments/1rcmlea/4_years_as_a_maintenance_coordinator_im_running/),” February 23, 2026.
[^19]: Reddit r/PropertyManagement, “[Maintenance coordination](https://www.reddit.com/r/PropertyManagement/comments/1rqnf89/maintenance_coordination/),” March 11, 2026.
[^20]: Reddit r/PropertyManagement, “[Experienced property manager](https://www.reddit.com/r/PropertyManagement/comments/1vqdbtq/experienced_property_manager_working_remotely_for/),” August 17, 2026.
[^21]: DHL Group, “[DHL boosts operational efficiency with HappyRobot AI agents](https://group.dhl.com/en/media-relations/press-releases/2025/dhl-boosts-operational-efficiency-and-customer-communications-with-happyrobots-ai-agents.html),” 2025.
[^22]: FourKites, “[United States Cold Storage scheduling automation](https://www.fourkites.ai/case-studies/united-states-cold-storage-automating-appointment-scheduling-with-digital-worker-alan),” accessed September 2026.
[^23]: Reddit r/FreightBrokers, “[Detention claims are becoming a nightmare](https://www.reddit.com/r/FreightBrokers/comments/1r1hbww/detention_claims_are_becoming_a_nightmare_is_it/),” June 27, 2026.
[^24]: Amalgamated Bank, “[Collaboration with FIS and Anthropic on financial-crime AI](https://www.amalgamatedbank.com/news/amalgamated-bank-announces-collaboration-fis-and-anthropic-advance-ai-financial-crimes),” May 7, 2026.
[^25]: FIS, “[FIS brings agentic AI to banking with Anthropic](https://fisglobal.gcs-web.com/news-releases/news-release-details/fis-brings-agentic-ai-banking-anthropic-starting-financial),” May 4, 2026.
[^26]: Reddit r/Banking, “[Piloting AI agents for AML casework](https://www.reddit.com/r/Banking/comments/1qe49dr/anyone_here_piloted_ai_agents_for_aml_casework/),” January 16, 2026.
[^27]: MaintainX, “[Autowash customer story](https://webflow.getmaintainx.com/case-studies/autowash),” accessed September 2026.
[^28]: Siemens, “[Industrial Copilot adopted by thyssenkrupp](https://press.siemens.com/global/en/pressrelease/siemens-industrial-copilot-expanded-adopted-thyssenkrupp),” accessed September 2026.
[^29]: Reddit r/maintenance, “[I spent three hours on a 15-minute job](https://www.reddit.com/r/maintenance/comments/1wc1g95/i_spent_3_hours_on_a_15min_job/),” September 9, 2026.
[^30]: Reddit r/maintenance, “[How much CMMS data is accurate?](https://www.reddit.com/r/maintenance/comments/1ug4757/be_honest_guys_how_much_of_your_cmms_data_is/),” June 26, 2026.
