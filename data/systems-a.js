// Systems 01–05. Content module consumed by build.js.
export default [

{
  id: 'sentinel',
  num: '01',
  name: 'Sentinel',
  subtitle: 'Public procurement integrity and collusion detection',
  themes: ['fraud', 'central', 'money'],
  tagline: 'Turns the Procurement Act’s new mandatory transparency data into a live map of who really wins public contracts — and who is connected to whom.',
  status: 'Statutory data source live since January 2026',

  problem: [
    'Government estimates fraud and error across the public sector at <strong>£55bn–£81bn a year</strong>, excluding tax and welfare. The Public Sector Fraud Authority reported <strong>£7.53bn saved</strong> in the last financial year and credited the result explicitly to AI and advanced data-matching — but that work concentrates on grants and payments, not on the award stage where procurement fraud originates.',
    'The classic red flags of bid-rigging are all detectable in data that is now public: single-bidder tenders, repeated runner-up patterns, suppliers sharing directors or registered addresses, contracts split just below thresholds, and award values clustering suspiciously close to estimates. Nobody in UK government is systematically looking for them across all buyers at once.',
    'The Procurement Act 2023 improved the raw material substantially. From <strong>1 January 2026</strong> contracting authorities must publish supplier performance for contracts over £5m, and from <strong>1 April 2026</strong> suppliers awarded below-threshold contracts must register on the Central Digital Platform and supply their Companies House number.',
    'Identifier coverage is contested, and the disagreement is itself the finding. Two independent measurements against the live feed in August 2026 disagreed sharply — roughly <strong>65% of supplier records carrying no scheme</strong> when counting company numbers on supplier entries alone, against roughly <strong>8%</strong> when counting the Procurement Act’s own organisation number across all parties. Both are defensible. The identifier exists; it is not where most consumers look for it. That organisation number is the key worth building on — it exists for councils, NHS trusts and unincorporated bodies with no company number, it survives group restructuring, and <strong>the debarment list is keyed on it</strong>. What nothing publishes is the mapping between it and Companies House.',
    'One constraint eliminates most of the academic literature. <strong>Individual bid prices are never published in UK procurement data</strong> — only aggregate statistics, and bidder counts appear on roughly 30% of awards. That rules out the entire statistical screen family: coefficient of variation, relative distance, normalised distance and the missing-bids test. Sentinel is designed around what exists rather than what the papers assume.',
    'The Open Contracting Partnership’s one-year analysis found <strong>57 of 71 integrity indicators are now computable</strong>, up from 35 under the old regime — and that <strong>single-bid tenders cost around 7% more</strong>. It also found institutional variation nobody is acting on: <strong>Bristol awards 95% of below-threshold contracts non-competitively; Leeds under 30%</strong>. Transparency International identified <strong>135 COVID contracts worth £15.3bn carrying three or more corruption red flags</strong>.',
    'One structural obstacle explains why this has not been done. Companies House publishes free bulk files for companies and PSCs, but <strong>there is no free bulk officers file</strong> — the directorship graph can only be assembled company-by-company through a rate-limited API across 4.93 million active companies. That single asymmetry is why UK director-network analysis is dominated by commercial products rather than public ones.'
  ],

  solution: [
    'Sentinel ingests the full public procurement record — Find a Tender, Contracts Finder and the Central Digital Platform — and resolves suppliers to Companies House entities. Because roughly two-thirds of records carry no usable identifier, that resolution is the system’s hardest engineering problem rather than a given: identifier where present, probabilistic name and address matching where not, with match confidence published on every link and low-confidence links never silently merged. It then builds a national graph connecting suppliers to their directors, persons with significant control, registered addresses and corporate parents.',
    'Against that graph it runs an indicator suite derived from established international practice — the EU’s Digital Whistleblower red-flag set, the World Bank’s procurement analytics, and Ukraine’s ProZorro/Dozorro monitoring model — scoring every award and every buyer for risk rather than accusing anyone of wrongdoing.',
    'Output is a triage queue for investigators, not a verdict. Each flag carries its evidence, its statistical basis and a plain-English explanation, so a commercial officer can dismiss it in thirty seconds or escalate it with a full audit trail.'
  ],

  datasets: [
    ['Central Digital Platform', 'Cabinet Office', 'Supplier registration, unique supplier identifiers, contract performance notices, payment performance. Mandatory below-threshold registration from 1 April 2026.'],
    ['Find a Tender Service', 'Cabinet Office', 'Statutory notices for above-threshold procurement across the UK public sector.'],
    ['Contracts Finder', 'Cabinet Office', 'Contract award notices, including below-threshold awards in England.'],
    ['Companies House API + bulk products', 'Companies House', 'Company records, officer appointments, PSC register, filing history, dissolution status. Free API under OGL v3.'],
    ['Local authority spend over £500', '300+ councils', 'Transaction-level payments. Fragmented schemas — normalised by System 10.'],
    ['Charity Commission register', 'Charity Commission', 'Trustee networks, for public bodies contracting with the voluntary sector.']
  ],

  features: [
    ['Supplier identity resolution', 'Every award tied to a canonical legal entity despite two-thirds of records lacking an identifier — surviving name changes, group restructures and typos, with confidence published per match. In one sample the same firm appeared as both “SOFTCAT LTD - FCA” and “SOFTCAT PLC”, with no company number on either.'],
    ['Connection graph', 'Shared directors, PSCs, registered addresses and corporate parents across bidders on the same tender — the single strongest signal of a rigged competition.'],
    ['Framework call-off concentration', 'The strongest collusion signal actually available in UK data. The related-processes field works reliably, exposing small supplier rings winning a disproportionate share of call-offs under one framework.'],
    ['Competition intensity index', 'Bidder counts by buyer, category and value band where published, benchmarked nationally. Coverage is reported as a metric rather than assumed.'],
    ['Threshold-splitting detection', 'Sequential awards to one supplier that individually fall below a procurement threshold and collectively exceed it.'],
    ['Performance-to-award linkage', 'Ties the new contract performance notices back to award characteristics, so buyers can see whether cheap bids actually deliver.'],
    ['Investigator case workspace', 'Flags triaged, assigned, annotated and closed with reasons, producing a defensible audit record and training data for calibration.'],
    ['Buyer self-service', 'Every contracting authority sees its own risk profile benchmarked against comparable bodies before anyone else does.']
  ],

  impact: [
    ['£55–81bn', 'Government’s own published estimate of annual fraud and error, excluding tax and welfare'],
    ['£7.53bn', 'Counter-fraud savings government attributes to AI and data-matching in the last year'],
    ['0', 'Suppliers on the debarment list after 18 months of the regime'],
    ['0.5%', 'Recovery rate on procurement spend that would repay the platform many times over']
  ],

  benefits: {
    government: [
      'Gives the Public Sector Fraud Authority — now within DWP — an award-stage capability to sit alongside its existing payment-stage work.',
      'Lets the Government Commercial Agency see competition health across the whole public estate rather than one framework at a time.',
      'Provides evidence for debarment decisions under the Procurement Act, which currently rest on limited investigative capacity.',
      'Turns a compliance burden — the new notice regime — into a management asset, which strengthens the case for the transparency rules themselves.'
    ],
    public: [
      'Money recovered or never lost is money not taken from services, using government’s own framing of savings as nurses and repaired roads.',
      'Local journalists and researchers get a usable national view of who wins public money in their area.',
      'Honest suppliers benefit: collusion suppresses competition and inflates prices, and SMEs are the main losers.'
    ]
  },

  phases: [
    ['Ingest and resolve', '3 months', 'Full historical load of Find a Tender, Contracts Finder and Companies House. Entity resolution benchmarked against a hand-labelled sample.'],
    ['Indicator calibration', '3 months', 'Red-flag suite tuned against known UK enforcement cases and international baselines. False-positive rate is the acceptance criterion, not flag volume.'],
    ['Investigator pilot', '6 months', 'Deployed with one central department and one combined authority. Success measured by cases escalated and value recovered, not flags produced.'],
    ['National rollout', '12 months', 'Buyer self-service opened to all contracting authorities; public interface published under OGL.']
  ],

  risks: [
    ['False accusation', 'Shared directors are common and usually innocent. The system scores risk and never asserts wrongdoing; every output is a prompt for human review with its evidence attached.'],
    ['Data quality upstream', 'Companies House data has known accuracy problems. Identity verification under ECCTA is improving this, and Sentinel reports data-quality defects back as a by-product.'],
    ['Gaming', 'Publishing the indicator logic teaches evasion. Core indicators are published for accountability; weightings and thresholds are held privately and rotated.'],
    ['The bid-level ceiling — stated plainly', 'Textbook cartel screening needs every bid including losing ones. Public data publishes awards, and independent analysis found the tenderer-count field is frequently recorded as zero. Sentinel can therefore detect single-bidder concentration, threshold splitting, rotation patterns and bidder relatedness — but not classical bid-rigging signatures. Going deeper requires buyer cooperation to supply their own tender records, which is a design assumption, not an afterthought. Any proposal claiming full cartel detection from open data alone is overselling.']
  ],

  buyer: 'Public Sector Fraud Authority (DWP), Government Commercial Agency, Cabinet Office',
  route: 'SBRI for the detection engine, then G-Cloud 15 Lot 2b for the platform',

  sources: [
    ['Procurement Act 2023: guide for suppliers', 'https://www.gov.uk/government/publications/procurement-act-2023-short-guides/the-procurement-act-2023-a-short-guide-for-suppliers-html'],
    ['Counter-fraud savings of £7.53bn', 'https://www.gov.uk/government/news/crackdown-on-public-sector-fraud-delivers-over-75-billion-of-savings-to-the-taxpayer'],
    ['National Fraud Initiative Strategy 2024–2028', 'https://assets.publishing.service.gov.uk/media/67b6f0dfbd116e3d7b1cf305/2025-02-11_PSFA_NFI_Strategy_final.pdf'],
    ['NAO: estimating and reporting fraud and error', 'https://www.nao.org.uk/insights/estimating-and-reporting-fraud-and-error/'],
    ['Procurement Act changes from 1 April 2026', 'https://www.techuk.org/resource/procurement-act-change-from-1-april-2026-public-sector-supplier-update.html']
  ]
},

{
  id: 'transit',
  num: '02',
  name: 'Transit',
  subtitle: 'Local government reorganisation data continuity',
  themes: ['local', 'operations', 'money'],
  tagline: 'The only system built for the single hardest deadline in UK local government: merging 134 councils into 38 by 1 April 2028 without losing the data that statutory services run on.',
  status: 'Vesting day 1 April 2028 — fixed statutory deadline',

  problem: [
    'Local government reorganisation will abolish <strong>134 councils and create 38 unitary authorities</strong>, with shadow elections in May 2027 and <strong>vesting day on 1 April 2028</strong>. Surrey has already gone first. Fourteen further areas were confirmed on 16 July 2026.',
    'Every merger means combining social care records, council tax and business rates bases, planning histories, licensing registers, land charges, housing waiting lists, SEND caseloads and debt ledgers — held in different systems, with different schemas, different identifiers and different retention practices. There is no shared tooling for this. Each area is solving it alone, from scratch, with consultants.',
    'The sector does not believe it will work. Only <strong>13% of councils</strong> think reorganisation will improve their finances, and <strong>76% of reorganising councils</strong> call reorganisation costs a fairly or very big problem — a higher share than any other pressure they report, including SEND.',
    'The failure mode is not abstract. Birmingham’s Oracle implementation is the canonical example of what a botched local government data migration costs, and it is the case senior officers cite when justifying spend on migration assurance.'
  ],

  solution: [
    'Transit is a reorganisation data platform: a shared, reusable toolkit that every merging area runs instead of inventing its own. It profiles the data estates of the predecessor councils, maps them to a common target schema, and tracks reconciliation to vesting day.',
    'It begins with discovery — automatically inventorying what data exists across predecessor authorities, in which systems, under which retention rules, and where identifiers collide. Two councils will both have a "Property 1042". Somebody has to resolve that before day one, and today nobody knows how many collisions exist until migration begins.',
    'It then provides golden-record reconciliation against national identifiers — UPRN for property, canonical person matching for caseloads — plus a continuity dashboard showing, service by service, whether the successor authority can lawfully deliver on 1 April 2028.',
    'Crucially it is built once and reused 38 times. That is the entire economic argument, and it is precisely the reuse-and-de-risking mission GDS Local was created to pursue.'
  ],

  datasets: [
    ['UPRN / AddressBase', 'Ordnance Survey / GeoPlace', 'Unique Property Reference Numbers — the canonical key for reconciling property records across predecessor systems.'],
    ['Local Land Charges register', 'HM Land Registry', 'Now digital and centralised, with 127 local authorities live — a working precedent for exactly this kind of consolidation.'],
    ['ONS geography portal', 'ONS', 'Boundary changes, ward and output area lookups, successor authority geographies.'],
    ['Council tax and NDR base returns', 'MHCLG', 'Taxbase and rating data by authority, used to reconcile revenue records.'],
    ['Local authority spend over £500', 'Predecessor councils', 'Supplier and contract continuity — which contracts transfer, which duplicate, which lapse.'],
    ['Structural Changes Orders', 'legislation.gov.uk', 'The statutory instrument for each area, defining precisely what transfers and when.']
  ],

  features: [
    ['Estate discovery', 'Automated inventory of systems, schemas, volumes, retention rules and data owners across all predecessor authorities in an area.'],
    ['Identifier collision detection', 'Finds every case where predecessor councils use the same key for different things, before it becomes a live service failure.'],
    ['Common target schema', 'A published, versioned schema per service domain, developed once and reused by every reorganising area — the anti-lock-in asset.'],
    ['Continuity dashboard', 'Service-by-service readiness against vesting day, with statutory duties mapped to the data required to discharge them.'],
    ['Contract and liability register', 'Every supplier contract, lease, debt and known liability transferring to the successor, reconciled across predecessors.'],
    ['Retention and disposal', 'Records management rules applied at merge, so the successor does not inherit an undocumented and unlawful data estate.'],
    ['Reuse library', 'Every mapping, transform and lesson published openly so area 15 does not repeat the work of area 1.']
  ],

  impact: [
    ['134 → 38', 'Councils being merged into unitary authorities'],
    ['1 Apr 2028', 'Vesting day — a fixed statutory deadline with no slippage available'],
    ['13%', 'Councils that believe reorganisation will improve their finances'],
    ['76%', 'Reorganising councils calling reorganisation costs a fairly or very big problem']
  ],

  benefits: {
    government: [
      'Converts 38 separate, consultant-led migrations into one funded national programme with reusable components — exactly the model GDS Local was set up to champion.',
      'Reduces the risk of a statutory service failure on 1 April 2028, which would be politically severe and legally exposed.',
      'Produces, as a by-product, the first accurate national picture of what data local government actually holds.',
      'Directly attacks the supplier lock-in that central government has named as the core problem in council technology.'
    ],
    public: [
      'Care packages, housing applications, school transport and benefits continue uninterrupted through reorganisation.',
      'Fewer public pounds spent on duplicated consultancy — the six section 114 councils alone spent £207m on external consultants since 2020-21.',
      'A cleaner, better-documented public record in the successor authority than in any of its predecessors.'
    ]
  },

  phases: [
    ['Discovery toolkit', '4 months', 'Estate inventory and collision detection, piloted with one confirmed reorganising area.'],
    ['Schema and mapping library', '6 months', 'Common target schemas for the highest-risk domains: social care, revenues, planning, housing.'],
    ['Continuity assurance', '6 months', 'Readiness dashboard in use across three areas ahead of the May 2027 shadow elections.'],
    ['Scale to all areas', '12 months', 'Available to every reorganising area with sufficient lead time before vesting day.']
  ],

  risks: [
    ['Timing', 'Vesting day is fixed. A platform arriving late is worthless. Scope is deliberately narrowed to discovery and reconciliation rather than replacing line-of-business systems.'],
    ['Incumbent resistance', 'Existing suppliers benefit from bespoke migration work. Mitigated by positioning Transit as assurance over migrations rather than a replacement for them.'],
    ['Sensitive data', 'Social care and housing records are highly sensitive. Transit operates on schemas, metadata and reconciliation reports by default, with record-level processing only under the authority’s own controllership.']
  ],

  buyer: 'MHCLG, GDS Local (DCMS), individual reorganising areas',
  route: 'DOS7 Lot 1 Digital Outcomes, with MHCLG programme funding',

  sources: [
    ['Local government reorganisation 2026 (Commons Library)', 'https://commonslibrary.parliament.uk/research-briefings/cbp-10494/'],
    ['Written statement on reorganisation decisions, 16 July 2026', 'https://questions-statements.parliament.uk/written-statements/detail/2026-07-16/hcws286'],
    ['LGIU State of Local Government Finance 2026', 'https://lgiu.org/2026-state-of-local-government-finance-in-england/'],
    ['GDS Local: building foundations for digital collaboration', 'https://gds.blog.gov.uk/2026/04/15/gds-local-building-the-foundations-for-digital-collaboration/'],
    ['HM Land Registry Local Land Charges programme', 'https://roadmap-for-modern-digital-government.campaign.gov.uk/digital-and-data-infrastructure/platforms-to-share-and-use-data']
  ]
},

{
  id: 'compass',
  num: '03',
  name: 'Compass',
  subtitle: 'SEND demand forecasting and transport optimisation',
  themes: ['local', 'children', 'money'],
  tagline: 'Parliament has formally found that government does not know whether £2.6bn of home-to-school transport is value for money. Compass is the missing evidence base.',
  status: 'Named parliamentary data gap, March 2026',

  problem: [
    'The Public Accounts Committee reported in March 2026 that <strong>"the Department does not know whether home to school transport is achieving value for money"</strong>, and that DfE <strong>lacks the data to oversee the service</strong> — it only began collecting who receives transport in February 2025, achieving a 75% response rate with partial answers.',
    'The spend is not marginal. Home-to-school transport cost <strong>£2.6bn in 2024-25</strong>, of which <strong>£2.0bn was SEND transport</strong>. SEND transport spending rose <strong>106% in real terms</strong> between 2015-16 and 2023-24. The median annual cost is <strong>£8,116 per SEND pupil</strong> against £1,526 for mainstream.',
    'The underlying driver is demand nobody forecasts well. EHCPs reached <strong>718,838 in January 2026, up 12.5% in a single year</strong> — the largest annual increase since plans were introduced in 2014. Only <strong>46.1%</strong> are issued within the statutory 20 weeks. Councils lose <strong>99% of SEND tribunal appeals</strong> while spending £153m a year defending them.',
    'Government has just written off <strong>90% of historic DSG deficits, worth over £5bn</strong>, conditional on councils submitting an approved local SEND reform plan. Those plans are due now, and most councils lack the analytical basis to write a credible one. New deficits continue to accrue on top.'
  ],

  solution: [
    'Compass does two connected jobs. It forecasts SEND demand at local authority and settlement level, and it optimises the transport network that demand generates.',
    'The forecasting side combines births, migration, school census, EHCP flow rates and housing completions to project EHCP volumes and specialist placement need three to seven years ahead — the planning horizon for creating specialist places, which is the only durable way to reduce both transport cost and independent placement cost.',
    'The transport side treats school transport as the routing problem it actually is. Given pupil locations, placement locations, statutory eligibility and individual needs, it identifies achievable route consolidation, exposes the cost of each placement decision at the point the decision is made, and quantifies the transport consequence of opening a specialist unit in one location versus another.',
    'The connection between the two is the point. A placement made without visibility of its seven-year transport cost is how a council ends up paying five figures a year to move one child, and no current system shows that number at the moment it matters.'
  ],

  datasets: [
    ['EHCP statistics', 'DfE', 'Plans in force, new plans, assessment requests, 20-week timeliness, by local authority. Published annually.'],
    ['School census / Get Information about Schools', 'DfE', 'Pupil-level characteristics, SEN status, school capacity and location.'],
    ['SCAP school capacity survey', 'DfE', 'Place planning capacity by authority and phase.'],
    ['ONS births and population projections', 'ONS', 'Cohort sizes feeding the forecast, by small area.'],
    ['Housing completions and permissions', 'MHCLG', 'New development driving future pupil numbers at settlement level.'],
    ['Indices of Multiple Deprivation', 'MHCLG', 'Correlates strongly with SEN identification rates.'],
    ['OS Open Roads / journey routing', 'Ordnance Survey', 'Network for genuine travel-time calculation rather than straight-line distance.'],
    ['SEND Tribunal statistics', 'MoJ', 'Appeal volumes and outcomes, for measuring decision quality.']
  ],

  features: [
    ['EHCP demand forecast', 'Three to seven year projections by authority and settlement, with confidence intervals and explicit driver attribution.'],
    ['Placement cost transparency', 'Full lifetime cost of a placement decision — fees plus transport plus review — surfaced at the point of decision.'],
    ['Route optimisation', 'Consolidation opportunities across the whole transport cohort, respecting individual needs and statutory eligibility.'],
    ['Specialist provision siting', 'Where to create places so that transport cost falls most, given projected demand geography.'],
    ['Post-16 modelling', 'The fastest-growing segment and the one excluded from the new funding formula — modelled explicitly.'],
    ['Tribunal risk signal', 'Decision patterns associated with appeals lost, so authorities can fix the decision rather than fund the defence.'],
    ['Reform plan evidence pack', 'Generates the analytical basis councils need for the DfE-approved local SEND reform plan that conditions their deficit write-off.']
  ],

  impact: [
    ['£2.0bn', 'Annual SEND home-to-school transport spend in England'],
    ['718,838', 'EHCPs in force at January 2026, up 12.5% in one year'],
    ['£8,116', 'Median annual SEND transport cost per pupil, against £1,526 mainstream'],
    ['1.3%', 'Local authority success rate at SEND tribunal — 99% of appeals upheld against them']
  ],

  benefits: {
    government: [
      'Answers the PAC finding directly, giving DfE the oversight data Parliament has said it does not have.',
      'Supports the condition attached to the £5bn deficit write-off — councils must submit credible SEND reform plans, and most currently cannot evidence them.',
      'Addresses the fastest-growing local government cost line with a forecasting horizon long enough to actually change it.',
      'Provides MHCLG with evidence on whether the new home-to-school transport funding formula works — which PAC noted it has no plan to monitor.'
    ],
    public: [
      'Children spend less time in taxis. Some SEND pupils currently travel hours a day.',
      'Faster, better-evidenced placement decisions reduce the adversarial tribunal process families are forced into — 25% of families reduce working hours fighting for support.',
      'Specialist places created where children actually live, rather than wherever capacity happened to exist.'
    ]
  },

  phases: [
    ['Forecast engine', '4 months', 'National EHCP demand model validated against outturn across all English authorities.'],
    ['Transport analytics', '4 months', 'Routing and consolidation modelling piloted with three county authorities.'],
    ['Decision support', '6 months', 'Placement cost transparency embedded in live casework with pilot authorities.'],
    ['National availability', '12 months', 'Offered to all authorities with high needs deficits, aligned to reform plan submission cycles.']
  ],

  risks: [
    ['Optimisation versus need', 'Route consolidation must never override an individual child’s assessed needs. Needs constraints are hard limits in the model, not weighted factors.'],
    ['Forecast credibility', 'EHCP growth has repeatedly outrun projections. Published back-testing against outturn, with intervals wide enough to be honest.'],
    ['Sensitivity', 'Children’s data of the highest sensitivity. Operates on aggregate and pseudonymised data by default; record-level work only under the authority’s controllership.']
  ],

  buyer: 'DfE, MHCLG, county councils and unitary authorities',
  route: 'DOS7 Lot 1, with DfE SEND reform programme funding',

  sources: [
    ['PAC 70th Report: home-to-school transport, 6 March 2026', 'https://publications.parliament.uk/pa/cm5901/cmselect/cmpubacc/1238/report.html'],
    ['NAO: home to school transport, 31 October 2025', 'https://www.nao.org.uk/reports/home-to-school-transport/'],
    ['DfE: education, health and care plans, January 2026', 'https://explore-education-statistics.service.gov.uk/find-statistics/education-health-and-care-plans'],
    ['Explanatory note on DSG deficits, 9 February 2026', 'https://www.gov.uk/government/publications/explanatory-note-on-the-governments-approach-to-dedicated-schools-grant-deficits/explanatory-note-on-the-governments-approach-dedicated-schools-grant-deficits'],
    ['Schools White Paper 2026: SEND reform (Commons Library)', 'https://commonslibrary.parliament.uk/research-briefings/cbp-10550/']
  ]
},

{
  id: 'threshold',
  num: '04',
  name: 'Threshold',
  subtitle: 'Temporary accommodation cost and placement intelligence',
  themes: ['local', 'housing', 'money'],
  tagline: 'Record homelessness, a subsidy gap frozen at 2011 rates, and no national view of what councils are actually paying for the same room.',
  status: 'Record levels every quarter for three years',

  problem: [
    'At 31 March 2026 there were <strong>135,580 households in temporary accommodation</strong> including <strong>177,530 children</strong> — both records since the series began in 2004. Children in temporary accommodation have set a record for <strong>twelve consecutive quarters</strong>.',
    'The financial mechanism is specific and fixable. Housing benefit subsidy for temporary accommodation is capped at <strong>90% of January 2011 Local Housing Allowance rates</strong> — frozen for fifteen years. Councils have already absorbed <strong>£1.5bn more than they have been reimbursed</strong>, projected to exceed <strong>£3.9bn by 2030</strong>. Gross spend hit <strong>£2.8bn in 2024-25, up 25% in one year</strong>.',
    'The fastest-growing and most expensive category is nightly-paid self-contained accommodation, now <strong>37.9% of all placements</strong> and rising. <strong>43,180 households are placed out of area</strong>, 32% of the total, and London authorities account for <strong>82%</strong> of those.',
    'What does not exist anywhere is a national view of price. Neighbouring councils bid against each other for the same rooms from the same landlords, with no visibility of what anyone else is paying. It is a market with hundreds of buyers, no price discovery, and desperate demand.',
    'And a new statutory duty has just created a data-matching requirement with no system behind it. The National Plan to End Homelessness commits to <strong>requiring local authorities to notify schools, GPs and health visitors when a child is placed in temporary accommodation</strong>. That means matching 177,530 frequently-moved children, often placed across borough boundaries, to three separate public services in near real time. Nothing currently does this.'
  ],

  solution: [
    'Threshold creates the price transparency that this market lacks. It normalises temporary accommodation spend from council payment data, links it to placement and duty statistics, and produces comparable unit costs by accommodation type, geography and duration.',
    'On top of that it models the subsidy gap precisely — for each authority, the difference between what it pays and what it can reclaim at the frozen 2011 rate — turning a national advocacy figure into an auditable per-authority number that can support both budgeting and reform.',
    'It also maps procurement behaviour: which providers operate across which councils, where the same landlord is charging materially different prices to different authorities, and where cross-boundary bidding is inflating cost for everyone. Neighbouring authorities can then coordinate rather than compete.',
    'Finally it identifies the prevention economics — comparing the cost of a placement against the cost of the intervention that would have prevented it, using each authority’s own data.'
  ],

  datasets: [
    ['Statutory homelessness statistics (H-CLIC)', 'MHCLG', 'Quarterly duties, placements, accommodation type, out-of-area placements, by authority.'],
    ['Local authority revenue outturn (RO4)', 'MHCLG', 'Homelessness and temporary accommodation expenditure, gross and net of subsidy.'],
    ['Local authority spend over £500', '300+ councils', 'Transaction-level payments to accommodation providers — the raw price signal.'],
    ['Local Housing Allowance rates', 'VOA / DWP', 'Current and historic rates, including the frozen January 2011 baseline that governs subsidy.'],
    ['Companies House', 'Companies House', 'Provider ownership structures, to see which landlords operate across multiple authorities.'],
    ['Energy Performance Certificates', 'MHCLG', 'Property-level condition and efficiency evidence for accommodation standards.'],
    ['ONS private rental prices', 'ONS', 'Market benchmark against which placement costs are assessed.']
  ],

  features: [
    ['Unit cost benchmarking', 'Comparable nightly and weekly costs by accommodation type and area, so an authority can see whether it is paying above the going rate.'],
    ['Subsidy gap calculator', 'Per-authority quantification of the gap between spend and reclaimable subsidy under the frozen 2011 cap.'],
    ['Provider mapping', 'Which providers operate where, under what ownership, at what price to which councils.'],
    ['Cross-boundary competition alerts', 'Where neighbouring authorities are bidding against each other for the same supply.'],
    ['Out-of-area impact', 'Placement flows between authorities, and the receiving-area service pressures they create.'],
    ['Prevention economics', 'Cost of placement against cost of the prevention measure that would have avoided it, using local data.'],
    ['Statutory breach early warning', 'Flags approaching six-week B&B limits for families before the limit is breached.']
  ],

  impact: [
    ['135,580', 'Households in temporary accommodation, March 2026 — a record'],
    ['177,530', 'Children in temporary accommodation — a record for twelve consecutive quarters'],
    ['£1.5bn', 'Subsidy gap already absorbed by councils, heading for £3.9bn by 2030'],
    ['£5.5m', 'Spent per day on homelessness by London boroughs in 2024-25']
  ],

  benefits: {
    government: [
      'Gives MHCLG the evidence base for the National Plan to End Homelessness targets, including eliminating unlawful B&B use beyond six weeks.',
      'Quantifies the subsidy gap authority by authority, informing whether and how to relink the temporary accommodation subsidy to current rates.',
      'Supports the new ringfence on prevention spend by showing what prevention actually costs against what placement costs.',
      'Directly serves the Prime Minister’s stated first instruction on ending rough sleeping and the linked temporary accommodation pressures.'
    ],
    public: [
      'Fewer families in unsuitable accommodation, and fewer placed far from schools, work and support networks.',
      'Money not lost to inflated placement prices is money available for prevention and for building.',
      'Transparency on who profits from homelessness placements, which is currently almost entirely opaque.'
    ]
  },

  phases: [
    ['Cost normalisation', '4 months', 'Council payment data normalised into comparable unit costs across a representative sample of authorities.'],
    ['Subsidy modelling', '3 months', 'Per-authority gap quantification validated against published outturn.'],
    ['London pilot', '6 months', 'Deployed across a group of London boroughs, where cost concentration and out-of-area placement are most severe.'],
    ['National rollout', '9 months', 'Extended to all authorities with significant temporary accommodation cohorts.']
  ],

  risks: [
    ['Commercial sensitivity', 'Providers will object to price transparency. The counter is that this is public money already published under transparency rules; Threshold aggregates what is already open.'],
    ['Data quality', 'Council spend data is inconsistently coded. Depends on the normalisation layer built for System 10.'],
    ['Perverse incentive', 'Published benchmarks can become a floor as well as a ceiling. Mitigated by publishing distributions rather than single reference prices.']
  ],

  buyer: 'MHCLG, London Councils, individual billing authorities',
  route: 'DOS7 Lot 1, with MHCLG homelessness programme funding',

  sources: [
    ['Statutory homelessness in England, January to March 2026', 'https://www.gov.uk/government/statistics/statutory-homelessness-in-england-january-to-march-2026/statutory-homelessness-in-england-january-to-march-2026'],
    ['LGA homelessness and rough sleeping position statement 2026', 'https://www.local.gov.uk/publications/homelessness-and-rough-sleeping-strategy-position-statement-2026'],
    ['IfG Performance Tracker 2025: homelessness', 'https://www.instituteforgovernment.org.uk/publication/performance-tracker-2025/local-services/homelessness'],
    ['A National Plan to End Homelessness', 'https://www.gov.uk/government/publications/a-national-plan-to-end-homelessness/a-national-plan-to-end-homelessness'],
    ['London Councils: £740m temporary accommodation shortfall', 'https://www.londoncouncils.gov.uk/news-and-press-releases/2025/ps740m-black-hole-londons-temporary-accommodation-crisis-draining']
  ]
},

{
  id: 'plumbline',
  num: '05',
  name: 'Plumbline',
  subtitle: 'Planning pipeline truth and delivery measurement',
  themes: ['housing', 'central', 'operations'],
  tagline: 'The headline says 91% of major applications are decided on time. The statutory figure is 19%. Plumbline measures what is actually happening.',
  status: 'MHCLG planning data standards due summer 2026',

  problem: [
    'Official statistics report that <strong>91% of major planning applications</strong> are decided within the statutory period <em>or an agreed extension</em>. Measured against the statutory 13-week deadline alone, the figure is <strong>19%</strong>. Around <strong>71% of major applications rely on extensions of time</strong>. The headline metric systematically conceals the real one.',
    'The measurement failures compound. The <strong>Housing Delivery Test’s latest official measurement is still 2023</strong>, published December 2024 — the mechanism that triggers presumption-in-favour sanctions is running three years stale. Only about <strong>30% of English planning authorities</strong> have an up-to-date adopted local plan.',
    'Meanwhile the pipeline is contracting. Planning permission was granted for <strong>209,781 homes in the year to September 2025 — the lowest 12-month total since 2013</strong>, against roughly 370,000 a year needed to support the target. Net additional dwellings were <strong>208,600 in 2024-25</strong>, and the government tracker records <strong>26% of the 1.5 million target</strong> delivered with the pledge rated off track.',
    'And 2025-26 outturn will not be published until around November 2026. The system that is meant to deliver 1.5 million homes cannot see its own current performance.'
  ],

  solution: [
    'Plumbline builds the honest measurement layer for the planning system, and does it in the window that MHCLG has itself created — planning data standards are due in <strong>summer 2026</strong>, with the National Infrastructure Spatial Tool entering private beta in <strong>November 2026</strong>.',
    'It reports determination performance against statutory deadlines and against extensions separately, always both, so that the gap is visible rather than hidden. It tracks extension-of-time usage as a first-class metric, since a system where 71% of major decisions need an extension has a capacity problem the headline denies.',
    'It maintains a live Housing Delivery Test estimate between official measurements, using permissions, starts, completions and building control data, so authorities and MHCLG can both see the trajectory rather than discovering it two years late.',
    'And it tracks the full pipeline from allocation through permission to completion, exposing where homes are being lost — refusal, appeal, viability, or permissions granted and never built.'
  ],

  datasets: [
    ['Planning application statistics (PS1/PS2)', 'MHCLG', 'Quarterly decisions, speed, and grant rates by authority.'],
    ['planning.data.gov.uk', 'MHCLG', 'The emerging national planning data platform, with standards due summer 2026.'],
    ['Housing supply: net additional dwellings', 'MHCLG', 'Annual outturn — the definitive delivery measure, published with a long lag.'],
    ['Indicators of new supply', 'MHCLG', 'Quarterly starts and completions, the leading indicator.'],
    ['Local Land Charges register', 'HM Land Registry', 'Digital, centralised, 127 authorities live, extending to building regulations.'],
    ['Planning Inspectorate statistics', 'PINS', 'Appeal volumes, outcomes and decision times.'],
    ['EPC lodgements', 'MHCLG', 'New dwelling completions with a much shorter lag than official statistics.'],
    ['Local plan status', 'MHCLG / PINS', 'Adoption dates and plan stage by authority.']
  ],

  features: [
    ['Dual-clock reporting', 'Every determination statistic reported against both statutory deadline and extended deadline, never one alone.'],
    ['Extension-of-time analytics', 'Who requests extensions, for what, how long, and whether they correlate with capacity or complexity.'],
    ['Live Housing Delivery Test', 'Continuous estimate between official measurements, so authorities see the trajectory rather than a retrospective verdict.'],
    ['Pipeline attrition', 'Where homes leave the pipeline between allocation, permission, start and completion.'],
    ['Capacity correlation', 'Determination performance against planning department staffing, linking delay to the resource gap.'],
    ['Appeal outcome prediction', 'Historic appeal patterns by authority and development type, informing both applicants and authorities.'],
    ['Standards conformance', 'Checks authority planning data against the MHCLG standards due summer 2026 and reports gaps back.']
  ],

  impact: [
    ['19%', 'Major applications actually decided within the statutory 13 weeks — against a 91% headline'],
    ['209,781', 'Homes permissioned in the year to September 2025 — lowest since 2013'],
    ['2023', 'The year of the most recent official Housing Delivery Test measurement'],
    ['26%', 'Of the 1.5 million homes target delivered, with the pledge rated off track']
  ],

  benefits: {
    government: [
      'Gives MHCLG honest, current performance data on the delivery mechanism for its highest-profile housing commitment.',
      'Supports and tests the planning data standards MHCLG is introducing in summer 2026, providing conformance feedback from day one.',
      'Makes the case for planning capacity investment evidentially rather than anecdotally — 97% of planning departments reported a skills gap in the last survey, itself now three years old.',
      'Complements rather than duplicates the National Infrastructure Spatial Tool, which addresses infrastructure rather than housing determination performance.'
    ],
    public: [
      'Applicants — including individual householders — can see realistic timelines for their authority rather than a misleading headline.',
      'Communities can see whether their council is genuinely delivering its plan or quietly missing it.',
      'Faster, better-resourced decisions mean homes built sooner for people who need them.'
    ]
  },

  phases: [
    ['Measurement layer', '3 months', 'Dual-clock reporting built from published statistics for all English authorities.'],
    ['Live delivery estimate', '4 months', 'Continuous Housing Delivery Test estimate validated against the 2023 official measurement.'],
    ['Standards conformance', '6 months', 'Aligned to MHCLG planning data standards as published in summer 2026.'],
    ['Authority rollout', '9 months', 'Self-service for all English planning authorities, with a public national view.']
  ],

  risks: [
    ['Political sensitivity', 'Publishing the gap between headline and statutory performance is uncomfortable. It is also already implicit in published statistics — Plumbline surfaces rather than reveals it.'],
    ['Overlap with MHCLG', 'Smaller than it appears. The April 2026 regulations mandate local plan timetables and housing requirement figures — <strong>not planning applications</strong>. The platform’s application dataset holds records from four councils, effectively three, and its collection has not run since 17 September 2025 while every other dataset collects daily. The gap is durable, not closing.'],
    ['Attribution', 'Delay has many causes, not all within an authority’s control. Reporting separates authority-controlled from applicant-controlled and consultee-driven delay.']
  ],

  buyer: 'MHCLG, planning authorities, Planning Inspectorate',
  route: 'DOS7 Lot 1, aligned to the MHCLG planning data standards programme',

  sources: [
    ['Planning applications in England, January to March 2026', 'https://www.gov.uk/government/statistics/planning-applications-in-england-january-to-march-2026/planning-applications-in-england-january-to-march-2026-statistical-release'],
    ['Housing supply: net additional dwellings 2024-25', 'https://www.gov.uk/government/statistics/housing-supply-net-additional-dwellings-england-2024-to-2025/housing-supply-net-additional-dwellings-england-2024-to-2025'],
    ['Full Fact: 1.5 million homes tracker', 'https://fullfact.org/government-tracker/1-5-million-homes/'],
    ['HBF: planning permissions hit 15-year low', 'https://www.hbf.co.uk/news/viability-crisis-sees-planning-permissions-for-new-homes-hit-15-year-low/'],
    ['Housing Delivery Test collection', 'https://www.gov.uk/government/collections/housing-delivery-test']
  ]
}

];
