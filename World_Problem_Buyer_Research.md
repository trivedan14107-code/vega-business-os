# The Best Near-Term Problem to Solve

## Executive conclusion

The strongest near-term startup problem is **speed-to-power for data centers and other large electrical loads**: utilities cannot connect enormous new loads quickly without risking grid reliability, while data-center developers lose strategic time waiting for firm capacity.

The product opportunity is a **grid-responsive interconnection and operations layer** that lets a utility grant earlier, conditional service in return for verifiable load flexibility. It would model the local operating envelope, coordinate computing workloads, batteries and on-site generation, transmit utility limits in real time, prove curtailment performance, and generate the evidence needed for tariffs, planners, operators and auditors.

This is not simply an energy dashboard. It is the shared control and evidence layer between a risk-averse utility and an impatient large-load customer.

## Why this problem ranks first

| Criterion | Finding | Score |
|---|---|---:|
| Pain | A delayed grid connection can strand a completed or planned data-center investment; utilities also face reliability, affordability and political risk. | 5/5 |
| Budget | PG&E published an estimated **$2.5 million** budget for an EPIC demonstration of the relevant operational capability. Data-center and grid infrastructure budgets are much larger, although they should not be confused with obtainable software revenue. | 5/5 |
| Urgency | Data-center electricity use is projected to rise sharply, interconnection queues are congested, and new flexible-load rules and pilots are being designed now. | 5/5 |
| Reachability | Utilities have long sales cycles, but named innovation programs, pilots, regulatory proceedings and large-load teams create identifiable entry points. | 4/5 |
| Defensibility | Validated grid models, control integrations, dispatch-performance history and bilateral operating agreements can form a meaningful moat. | 5/5 |
| **Total** | Highest result across the screened opportunity set. | **24/25** |

The Department of Energy says the United States faces surging electricity demand, a generation-interconnection backlog and aging transmission infrastructure. It notes that data centers consumed about 4.4% of U.S. electricity in 2023 and could reach as much as 12% by 2028.[^1] Dominion Energy says unprecedented growth in both the number and magnitude of large-load requests forced it to establish a formal queue and that service may be delayed to protect reliability.[^2]

The commercial exchange is unusually clear: **flexibility in return for speed**. PG&E describes an operating tool that forecasts constraints, communicates capacity limits and allows flexible customers to connect sooner. Its December 2025 workshop identified the operational tool as the key element enabling speed in exchange for flexibility and assigned the demonstration an estimated $2.5 million budget.[^3] PG&E's existing Flex Connect program has already shown that customers can obtain needed capacity during most hours while accepting constraints during grid stress.[^4]

## Recommended product

### Grid-responsive speed-to-power OS

The initial product should support one constrained utility territory and one class of large load.

1. **Connection scenario engine:** simulate a proposed load ramp against feeder, substation and transmission constraints; compare firm, phased and flexible service.
2. **Operating envelope:** convert utility constraints into machine-readable hourly or real-time capacity limits.
3. **Site orchestrator:** dispatch movable compute, batteries, cooling and approved on-site generation while protecting service-level objectives.
4. **Performance ledger:** preserve tamper-evident telemetry, curtailment instructions, responses, exceptions and root-cause analysis.
5. **Tariff and contract evidence:** produce reports for planners, operators, regulators and the large-load customer's energy team.

The best entry wedge is **planning plus verification**, not autonomous control on day one. A first pilot can model historical constraints, replay proposed dispatches and verify a limited live response. Control authority can expand only after both parties trust the results.

## Named organizations with buyer-readiness signals

“Ready to buy” is used carefully. Tier A indicates a public pilot, program, procurement specification or commercial deployment. Tier B indicates disclosed operational need, formal requirements or committed investment, but no public open procurement was found.

| Organization | Readiness | Public signal | Likely buyer |
|---|---|---|---|
| **PG&E** | **Tier A** | Published the speed-for-flexibility problem, an operational-tool concept and an estimated **$2.5M** EPIC demonstration budget; it also operates Flex Connect. | Large-load programs, grid planning, distribution operations, innovation/R&D |
| **Silicon Valley Power** | **Tier A** | Participating in a commercial multi-megawatt flexible AI deployment with NVIDIA and Emerald AI, demonstrating willingness to operate this category of solution. | Utility engineering, system operations, key accounts |
| **Salt River Project** | **Tier A** | Participated in EPRI's DCFlex demonstrations, including software-led tests of data-center flexibility. | Grid operations, resource planning, strategic energy management |
| **Iron Mountain** | **Tier A/B** | DOE records a data-center flexibility project involving microgrids at Iron Mountain sites in Virginia and South Carolina. | Energy and sustainability, data-center operations, infrastructure |
| **Microsoft** | **Tier B** | Says it will contract early and pay for transmission/substation upgrades; publicly advocates faster interconnection and submitted comments on California flexible-load service. | Energy procurement, cloud infrastructure, site development |
| **Dominion Energy** | **Tier B** | Created a formal large-load queue and detailed technical requirements for ride-through, mitigation and possible curtailment/disconnection. | Large-load interconnection, transmission planning, system operations |
| **Google** | **Tier B** | Has signed utility agreements using data-center flexibility in several U.S. territories, according to material in a 2026 DOE proceeding. | Data-center energy, infrastructure, grid partnerships |
| **CAISO and participating transmission owners** | **Ecosystem target** | Developing flexible large-load interconnection options and debating required communications, control, protection and remote-disconnection capabilities. | Market design, transmission planning, participating utility operations |

PG&E is the clearest first account because its public materials define both the missing capability and a pilot-scale budget. Silicon Valley Power and Salt River Project are strong design partners but have existing pilot relationships. Microsoft, Iron Mountain and other large-load customers can be the second side of a utility-led pilot.

## Competitive reality

This is a validated market, not empty whitespace. Emerald AI, NVIDIA, EPRI participants, established utility-control vendors and data-center energy-management suppliers are already active. A generic “AI optimizes energy” pitch will not survive.

The differentiated wedge should be:

- vendor-neutral interoperability across utility control systems and site equipment;
- utility-grade planning and certification before live control;
- contractual proof of whether the customer followed each operating limit;
- workload-aware flexibility that does not expose sensitive computing details;
- support for advanced manufacturing, EV charging and batteries as well as data centers.

The major risks are utility sales cycles, cyber and safety certification, access to network models, liability for missed curtailment, and incumbent bundling. These risks favor a paid simulation/verification pilot before full closed-loop dispatch.

## First customer offer

Offer a **12-week paid feasibility and replay pilot** for one proposed or constrained connection:

- ingest interval load, planned ramp, local limits and available flexible assets;
- quantify how much firm capacity can be deferred and how many hours of limitation would have occurred historically;
- replay utility instructions against a digital representation of the site;
- produce an auditable operating agreement and pilot-control specification;
- define a live test with explicit safety boundaries and human override.

Success should be measured by months of connection time avoided, megawatts connected before upgrades, hours and depth of curtailment, service-level impact, response accuracy, and avoided grid-upgrade cost. Pricing should be discovered with buyers; the published $2.5 million PG&E demonstration is a category-level budget marker, not a justified software price.

## Ninety-day buyer validation plan

### Days 1–20: prove the problem

Interview 15 people across three roles: utility large-load/interconnection leaders, data-center energy/site leaders, and independent system-planning engineers. Ask for the last failed or delayed connection study, required telemetry, allowable control latency, liability allocation and internal approval path. Do not begin with a product demo.

### Days 21–45: build the evidence prototype

Create a scenario model that compares firm connection, phased ramp and flexible connection for one representative site. Generate an operating-envelope feed and a human-readable evidence report. Use public or synthetic network data until a buyer provides protected data.

### Days 46–70: secure a design partner

Approach PG&E first, then municipal utilities and pilot participants where the category is already accepted. In parallel, approach a data-center or industrial customer that has an actual delayed site. Seek a paid feasibility engagement, data-access agreement and named operational sponsor.

### Days 71–90: contract the live boundary

Agree on a non-production replay or narrowly bounded live test. Define who can issue a constraint, who may override it, how performance is measured, what happens when communications fail, and which evidence the utility needs for regulator acceptance.

## Cross-domain comparison

| Rank | Problem | Score | Why it is attractive | Why it did not rank first |
|---:|---|---:|---|---|
| 1 | Grid-responsive speed-to-power | **24/25** | Explicit pilot budget, acute two-sided pain, fast-growing constraint, strong data/control moat | Hard integrations and credible incumbent activity |
| 2 | DORA third-party ICT evidence exchange | **23/25** | Live EU enforcement, large outsourced-ICT spend, manual evidence work, supplier-network moat | Strong GRC incumbents; hiring signals are clearer than public procurement signals |
| 3 | Closed-loop PFAS compliance and destruction | **23/25** | Human importance, regulatory deadline, water-utility projects worth tens to hundreds of millions | Science, hardware, permitting and capital intensity make it a harder startup |
| 4 | Prior-authorization evidence and exception orchestration | **22/25** | CMS deadline, roughly $15B estimated ten-year savings, enormous provider burden | Crowded field and difficult EHR/payer integrations |
| 5 | Bank risk-data lineage and control automation | **22/25** | Decade-long regulatory failure and high defensibility once embedded | Very long bank sales cycles and powerful incumbents |
| 6 | Precision clinical-trial enrollment workflow | **21/25** | Pharmaceutical R&D budgets and measurable enrollment value | Data access and established clinical/CRO platforms |
| 7 | Insurance claims agents with auditable decisions | **21/25** | Allianz reported an 80% cycle-time reduction; insurers are inviting startups | Large carriers are building directly with model vendors |
| 8 | Methane MRV evidence network | **21/25** | EU import obligations beginning in 2027 and cross-company data complexity | Major producers can build internally; standards still evolve |

## Best software-only alternative

If the founding team lacks power-systems and utility-control expertise, pursue **DORA third-party ICT evidence exchange** instead. The focused wedge is the quarterly evidence chase for a financial institution's 20 most critical suppliers: maintain the DORA register, map contracts and subcontractors to critical functions, ingest live control evidence, manage exit-plan proof and assemble regulator-ready audit packages.

The ECB reports that an average significant bank spends €83.9 million on outsourced ICT services and that cloud outsourcing expenditure rose 13.5% year over year.[^5] It continues to find deficiencies in third-party risk, continuity and exit planning while increasing supervisory attention through 2026–28.[^6] ING and Zurich posted 2026 roles devoted to DORA evidence, reporting, supplier assessment and audit remediation—strong evidence that the work remains labor-intensive, although not proof of an open vendor purchase.[^7]

## Sources

[^1]: U.S. Department of Energy, “[Smart Transmission Tools Modernize America's Power Grid](https://www.energy.gov/cmei/systems/articles/smart-transmission-tools-modernize-americas-power-grid),” November 13, 2025.
[^2]: Dominion Energy, “[GS-5 Large Load Rate Class Report](https://sustainability.dominionenergy.com/GS-5%20Large%20Load%20Rate%20Class%20Report.pdf),” 2026; Dominion Energy, “[Facility Interconnection Requirements](https://www.dominionenergy.com/-/media/content/large-business-services/pdfs/virginia/facility-interconnection-requirements.pdf),” October 2025.
[^3]: PG&E, “[EPIC 4 Workshop](https://www.pge.com/content/dam/pge/docs/about/corporate-responsibility-and-sustainability/12-15-2025-epic-4-workshop.pdf),” December 15, 2025; PG&E, “[2025 Innovation Pitch Fest Problem Statements](https://www.pge.com/assets/pge/docs/about/pge-systems/2025-innovation-pitch-fest-preread.pdf),” 2025.
[^4]: Utility Dive, “[PG&E sees rising interest in customer-driven flexible interconnection pilot](https://www.utilitydive.com/news/pge-sees-rising-interest-in-customer-driven-flexible-interconnection-pil/829447/),” September 2, 2026.
[^5]: European Central Bank, “[Banks' outsourcing landscape: an overview of current trends and supervisory challenges](https://www.bankingsupervision.europa.eu/press/supervisory-newsletters/newsletter/2025/html/ssm.nl250219_2.cs.html),” February 19, 2025.
[^6]: European Central Bank, “[Supervisory priorities 2026–28](https://www.bankingsupervision.europa.eu/framework/priorities/html/ssm.supervisory_priorities202511.en.html),” 2025; European Central Bank, “[2025 SREP aggregated results](https://www.bankingsupervision.europa.eu/activities/srep/2025/html/ssm.srep202511_aggregatedresults2025.en.html),” 2025.
[^7]: ING, “[DORA specialist](https://careers.ing.com/ro/post-vacant/warsaw/starszy-a-specjalista-ka-ds-dora/3121/41539414976),” July 20, 2026; ING, “[Senior Third Party Cyber Assurance Expert](https://careers.ing.com/it/lavoro/madrid/senior-third-party-cyber-assurance-expert/3121/34515991872),” July 21, 2026; Zurich, “[Risk & Internal Control Specialist](https://www.careers.zurich.com/job/Stockholm-Risk-%26-Internal-Control-Specialist/1367581557/),” 2026.

Additional primary evidence: Microsoft, “[Community-first AI infrastructure](https://blogs.microsoft.com/on-the-issues/2026/01/13/community-first-ai-infrastructure/),” January 13, 2026; U.S. Department of Energy, “[Data Center Flexibility as a Grid Enhancing Technology](https://www.energy.gov/nepa/articles/cx-035792-data-center-flexibility-grid-enhancing-technology),” April 22, 2026; California ISO, “[Flexible large-load interconnection stakeholder comments](https://stakeholdercenter.prod.caiso.com/Comments/AllComments/43a11ec9-fe21-4255-bb1c-336ad3703845),” September 2026; CMS, “[Interoperability and Prior Authorization Final Rule](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f),” January 2024; American Hospital Association, “[Costs of Caring](https://www.aha.org/costsofcaring),” 2026; European Commission, “[Methane emissions](https://energy.ec.europa.eu/topics/carbon-management-and-fossil-fuels/methane-emissions_en),” accessed September 2026; U.S. EPA, “[PFAS drinking-water regulation](https://www.epa.gov/sdwa/and-polyfluoroalkyl-substances-pfas),” accessed September 2026.
