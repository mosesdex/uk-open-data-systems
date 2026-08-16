// Systems 06–10. Content module consumed by build.js.
export default [

{
  id: 'highwater',
  num: '06',
  name: 'Highwater',
  subtitle: 'Floodplain development monitoring',
  themes: ['climate', 'housing', 'central'],
  tagline: 'The Environment Agency does not know what councils decided in 30% of its own flood objections. That is 7,011 unanswered cases — and the number granted against its advice has more than tripled in three years.',
  status: 'Computed from the published dataset, August 2026',

  problem: [
    'The Environment Agency publishes a list of every planning application it objected to on flood risk grounds. Parsed in full, it contains <strong>23,336 records across 426 planning authorities</strong> for 2016-17 to 2024-25. Of those, <strong>67.2% show EA advice was followed</strong>, <strong>2.7% (635 applications, 2,949 homes) were granted against its advice</strong> — and for <strong>30.0%, or 7,011 applications, the outcome is simply unknown</strong>. The EA states plainly that it records the outcome of about 68% of applications and uses a sample.',
    'The absolute numbers rose sharply: permissions granted against EA flood advice went <strong>28 in 2021-22 to 102 in 2024-25</strong>. But the honest reading is more interesting than the alarming one. The <strong>rate</strong> stayed roughly flat at 3–5% across all nine years, which is consistent with the government line that 96% of decisions follow EA advice. More homes were permitted against advice because more applications were objected to — not because councils became more willing to override. Anyone presenting the 3.6-fold rise without the flat rate will be taken apart in the first meeting, and rightly.',
    'The EA reports "over 97% compliance" with its advice. Aviva, joining Ordnance Survey AddressBase to the national flood risk assessment, found <strong>one in nine new English homes built 2022–2024 is in a medium or high flood risk area</strong> — 43,937 homes. Both statements are true. The gap between them exists because the EA counts objections it made, not homes that were built, and because <strong>surface water flooding sits largely outside its objection trigger</strong> despite being the fastest-growing risk.',
    'Two structural defects make the official dataset nearly unusable. It carries <strong>no spatial reference of any kind</strong> — no coordinates, no UPRN, no postcode, no site address — so it cannot be joined to flood maps without scraping 426 council portals. And each annual release silently restates history with <strong>no versioned archive</strong>, so the trend above is not reconstructible from official sources by anyone who did not save previous years’ files.'
  ],

  solution: [
    'Highwater turns a flat administrative list into a spatial, longitudinal evidence base. It resolves every objection record to a site location by matching authority planning references against council portals, producing the geocoded national dataset that does not currently exist.',
    'It then closes the outcome gap the EA does not close itself, retrieving decision notices for the 7,011 unknown cases. If the granted-against-advice rate in the unknown set even approximates the known set, the true national compliance figure is materially worse than the published one — and that is a finding government needs before it changes the policy.',
    'It maintains a versioned archive of every annual release, so trends survive the EA’s restatements. This matters urgently: the statutory consultee reform proposes <strong>removing the use of objections where flood directions do not apply</strong>, which would break the only national time series that exists, at the moment it is most needed.',
    'And it addresses the blind spot directly, cross-referencing new residential permissions against surface water risk — the category where the EA has no objection trigger and therefore no data exists at all, despite the December 2024 NPPF extending the sequential test to cover it.'
  ],

  datasets: [
    ['EA objections to planning applications', 'Environment Agency', 'ODS, OGL v3, annual since 2015. 23,336 records, 426 authorities. No spatial reference — the core defect Highwater fixes.'],
    ['Flood Map for Planning (Zones 2 and 3)', 'Environment Agency', 'Open OGC API Features endpoint, no API key required.'],
    ['NaFRA2 national flood risk assessment', 'Environment Agency', 'OGL v3, 2m grid resolution, covers rivers, sea and surface water. 6.3 million properties currently at risk.'],
    ['planning.data.gov.uk', 'MHCLG', 'Flood risk zone, flood storage area and flood risk level datasets. Planning applications remain incomplete — see Plumbline.'],
    ['EPC lodgements', 'MHCLG', 'New-build certificates are the only near-national, address-level completion proxy.'],
    ['Net additional dwellings (Live Table 122)', 'MHCLG', 'District-level completions for reconciliation.'],
    ['EA climate change allowances', 'Environment Agency', 'Currently HTML tables only, last updated May 2022. Highwater publishes them as an open API keyed to catchment.']
  ],

  features: [
    ['National geocoding', 'Every objection resolved to site location and UPRN — beating the best existing volunteer effort, which stalls at 31% coverage.'],
    ['Outcome gap closure', 'Decision retrieval for the 7,011 cases where the Environment Agency does not know what happened.'],
    ['Versioned archive', 'Every annual release preserved, so trends survive silent restatement and the coming policy break stays measurable.'],
    ['Surface water exposure', 'New permissions cross-referenced against surface water risk — the unmeasured category.'],
    ['Cumulative catchment impact', 'Permissions aggregated by management catchment, the analysis the Environmental Audit Committee recommended and government declined to commission.'],
    ['Developer accountability graph', 'Repeat applicants and agents across objected schemes, recoverable from portal documents and never yet assembled nationally.'],
    ['Climate allowances API', 'The EA’s allowances liberated from four-year-old HTML tables into a queryable service for every flood risk assessment author in the country.']
  ],

  impact: [
    ['7,011', 'Objection outcomes the Environment Agency does not know — 30% of its own dataset'],
    ['3–5%', 'Rate of permissions against EA flood advice — flat for nine years, while counts tripled'],
    ['1 in 9', 'New English homes built 2022–2024 in medium or high flood risk areas'],
    ['6.3m', 'Properties in England currently at flood risk, rising toward 8m by mid-century']
  ],

  benefits: {
    government: [
      'Lets the Environment Agency evidence its own claim that £1 of planning advice avoids £12 of future flood damage, which its 68% sample cannot currently support.',
      'Gives Defra the evidence to judge whether statutory consultee reform degrades the flood evidence base before it enacts the change.',
      'Supplies the Climate Change Committee with a defensible national adaptation indicator, which it currently lacks in any non-licensed form.',
      'Supports the £4.2bn flood investment programme by showing where new liability is being created faster than defences are being built.'
    ],
    public: [
      'Homebuyers can see whether a new development was permitted against flood advice — currently almost impossible to discover.',
      'New-build homes completed after 2009 are excluded from Flood Re, so every home built in a high-risk area is a future uninsurable liability for its owner.',
      'Communities gain evidence for local scrutiny of decisions taken against expert advice.'
    ]
  },

  phases: [
    ['Parse and archive', '2 months', 'Full ingest of all published releases, versioned, with the trend analysis published as an open finding.'],
    ['Geocoding at scale', '5 months', 'Portal resolution across all 426 authorities, targeting coverage well beyond the 31% volunteer ceiling.'],
    ['Outcome recovery', '4 months', 'Decision retrieval for the unknown cohort, with the revised national compliance figure published.'],
    ['Surface water and catchment', '6 months', 'Risk cross-referencing and cumulative catchment analytics released to EA, Defra and CCC.']
  ],

  risks: [
    ['Portal scraping fragility', 'Council portals change without notice. Mitigated by treating coverage as a published metric rather than a silent assumption, and by degrading gracefully to partial coverage with stated confidence.'],
    ['Policy break', 'If objections are removed where flood directions do not apply, the series discontinues. Highwater’s archive makes the break visible rather than invisible — arguably its most valuable function.'],
    ['Contested framing', 'Authorities will object to being ranked. Reporting presents context — housing pressure, viability, defence status — rather than a naked league table.']
  ],

  buyer: 'Environment Agency (FCRM), Defra, MHCLG Planning, Climate Change Committee',
  route: 'SBRI for the geocoding and recovery engine, then DOS7 for the service',

  sources: [
    ['EA objections to planning on the basis of flood risk', 'https://www.gov.uk/government/publications/environment-agency-objections-to-planning-on-the-basis-of-flood-risk'],
    ['How to use the list of planning objections (the 68% caveat)', 'https://www.gov.uk/government/publications/environment-agency-objections-to-planning-on-the-basis-of-flood-risk/how-to-use-the-list-of-planning-objections'],
    ['National assessment of flood and coastal erosion risk 2024', 'https://www.gov.uk/government/publications/national-assessment-of-flood-and-coastal-erosion-risk-in-england-2024/national-assessment-of-flood-and-coastal-erosion-risk-in-england-2024'],
    ['EAC Flood resilience in England: government response', 'https://publications.parliament.uk/pa/cm5901/cmselect/cmenvaud/1591/report.html'],
    ['Reforms to the statutory consultee system', 'https://www.gov.uk/government/consultations/reforms-to-the-statutory-consultee-system/reforms-to-the-statutory-consultee-system']
  ]
},

{
  id: 'catchment',
  num: '07',
  name: 'Catchment',
  subtitle: 'School place planning at the geography that matters',
  themes: ['children', 'local', 'operations'],
  tagline: 'England has 3,651 pupil planning areas and publishes the boundaries of none of them. Councils get capacity data they cannot map, while surplus and shortage sit side by side inside the same authority.',
  status: 'NAO reported the mismatch in April 2026',

  problem: [
    'The numbers look contradictory until you look below local authority level. England has <strong>1.2 million unfilled school places — 13% of all capacity</strong>, including <strong>680,000 unfilled primary places, the highest since collection began</strong>. At the same time <strong>about 3,000 schools are at or over capacity</strong>.',
    'The National Audit Office explained why in April 2026: <strong>"Of local authorities forecasting falling primary school pupil numbers, 66% expect to see numbers increase in one or more of the smaller areas for which they gather data."</strong> Surplus and shortage coexist inside single councils. It is a spatial allocation failure, invisible in every published statistic.',
    'The unit where it happens is the pupil planning area. There are <strong>3,651 of them across 153 authorities</strong>, each defined by its own council. DfE publishes school capacity data at planning-area level — and <strong>the boundaries are published nowhere as open geospatial data</strong>. No shapefile, no GeoJSON, no lookup to any standard geography. Councils receive rows they cannot map, compare, or join to anything.',
    'The inputs DfE expects councils to forecast from do not exist at that geography either. ONS publishes 2025 fertility at country level only. There is <strong>no national site-level housing completions dataset</strong>. And DfE’s own National Pupil Projections are <strong>national level only</strong>, with the horizon cut from ten years to five because of migration uncertainty.',
    'The consequence is measurable: the London Assembly had to send <strong>freedom of information requests to all 33 boroughs</strong> to count how many schools had closed and why, because the data does not exist. Meanwhile EHCPs reached 718,838 with <strong>211,400 pupils in special schools against 160,000 special school places</strong> — and the NAO records that DfE <strong>"does not know how many spaces are available in mainstream schools or other settings."</strong>'
  ],

  solution: [
    'Catchment starts with the cheapest high-value fix in this entire portfolio: publishing an open, versioned geography for the 3,651 pupil planning areas, reconstructed from the school membership DfE already publishes, with a lookup to standard census geographies. One artefact, and every join in the domain becomes possible.',
    'On that foundation it builds small-area demand forecasting — apportioning births, internal migration and new-build completions to planning areas to project reception intake where it actually occurs, rather than at the authority level where the signal cancels out.',
    'It then makes the NAO’s finding visible: a national map of where surplus and shortage sit within the same authority, authority by authority and area by area.',
    'And it offers the one genuinely constructive answer to the surplus problem. Rather than closing schools that will be needed again when housing lands, it identifies mainstream schools with persistent surplus within travel distance of unmet specialist demand — converting empty classrooms into the scarcest asset in the system. DfE’s own estates strategy commits to re-using surplus space and has no tooling to find it.'
  ],

  datasets: [
    ['School Capacity (SCAP)', 'DfE', 'Capacity, forecasts and planned changes at national, regional, authority, planning area and school level. Notably absent from the DfE statistics API.'],
    ['Get Information About Schools (GIAS)', 'DfE', 'Daily bulk CSV, no authentication. 52,486 establishments, 135 fields, including closure dates and reasons.'],
    ['National Pupil Projections', 'DfE', 'National level only — the gap Catchment fills locally.'],
    ['EHCP statistics', 'DfE', 'Plans by placement type, for the specialist capacity gap analysis.'],
    ['ONS births and internal migration', 'ONS', 'Cohort inputs, apportioned to planning areas.'],
    ['EPC new-build lodgements', 'MHCLG', 'Address-level, near-real-time completion proxy — the only one available nationally.'],
    ['ONS Open Geography Portal', 'ONS', 'Standard boundaries for the planning-area lookup.']
  ],

  features: [
    ['Open planning-area geography', 'The 3,651 boundaries reconstructed and published openly with a lookup to census geographies — the missing key to the whole domain.'],
    ['Small-area intake forecasting', 'Reception and Year 7 projections at planning-area level, not authority level.'],
    ['Surplus–shortage adjacency map', 'The NAO’s 66% finding made specific: which areas within each council are growing while the council overall shrinks.'],
    ['Specialist conversion finder', 'Mainstream schools with persistent surplus within travel distance of unmet EHCP demand.'],
    ['Closure register with reasons', 'GIAS closures cleaned of academisation artefacts and joined to school organisation decisions — the dataset the London Assembly had to FOI.'],
    ['Reversibility warning', 'Flags closures that the housing pipeline suggests would need reversing, given the projected demand trough.'],
    ['Funding impact projection', 'School-level income falls modelled from roll projections, since roughly 90% of funding follows pupils.']
  ],

  impact: [
    ['3,651', 'Pupil planning areas whose boundaries are published nowhere'],
    ['1.2m', 'Unfilled school places — alongside 3,000 schools at or over capacity'],
    ['66%', 'Councils with falling primary rolls that expect growth in one or more sub-areas'],
    ['211,400 / 160,000', 'EHCP pupils in special schools against available special school places']
  ],

  benefits: {
    government: [
      'Answers the NAO’s April 2026 findings directly, including that DfE does not use capacity data to monitor how schools respond.',
      'Gives the DfE Pupil Place Planning team — the named owner of SCAP and Basic Need — the sub-authority evidence its own allocation formula depends on.',
      'Supports the February 2026 ten-year estates strategy commitment to re-use surplus space, which currently has no supporting tooling.',
      'Connects mainstream surplus to the specialist shortage driving high needs deficits, linking two problems currently managed on entirely separate tracks.'
    ],
    public: [
      'Fewer schools closed that are needed again five years later, and fewer children in overcrowded classrooms two miles from empty ones.',
      'Specialist places created by converting surplus capacity, reducing both waiting times and transport distances for children with EHCPs.',
      'Parents and governors can see the actual demand picture for their area rather than an authority-wide average that hides it.'
    ]
  },

  phases: [
    ['Planning-area geography', '3 months', 'Boundaries reconstructed, validated with a sample of authorities, published openly under OGL.'],
    ['Demand nowcasting', '4 months', 'Small-area forecasts back-tested against actual intake across all authorities.'],
    ['Mismatch mapping', '3 months', 'National surplus–shortage adjacency analysis published.'],
    ['Conversion and closure tools', '6 months', 'Specialist conversion finder and national closure register released to DfE and councils.']
  ],

  risks: [
    ['Boundary accuracy', 'Reconstructed geographies are approximations of authority-defined areas. Published with explicit confidence and a correction route for councils to submit their true boundaries — which improves the asset over time.'],
    ['Closure sensitivity', 'School closure is intensely political. Catchment provides evidence and explicitly models reversibility rather than recommending closures.'],
    ['Schema instability', 'GIAS warns its bulk fields and field order can change without notice. Handled by schema-tolerant ingestion with change alerting.']
  ],

  buyer: 'DfE Pupil Place Planning and Regions Group, councils, London Councils and the GLA',
  route: 'DOS7 Lot 1, with DfE capital and place-planning funding',

  sources: [
    ['NAO: Responding to changing demand for school places, April 2026', 'https://www.nao.org.uk/reports/responding-to-changing-demand-for-school-places/'],
    ['DfE School Capacity 2024/25', 'https://explore-education-statistics.service.gov.uk/find-statistics/school-capacity/2024-25'],
    ['Local authority pupil planning areas guidance', 'https://www.gov.uk/government/publications/local-authority-pupil-planning-areas-guide-for-local-authorities/local-authority-pupil-planning-areas-guidance'],
    ['NAO: Support for children and young people with SEN', 'https://www.nao.org.uk/press-releases/special-educational-needs-system-is-financially-unsustainable/'],
    ['London Assembly analysis of borough FOI responses', 'https://www.london.gov.uk/sites/default/files/2026-02/Read%20analysis%20of%20responses%20to%20FOIs.pdf']
  ]
},

{
  id: 'waypoint',
  num: '08',
  name: 'Waypoint',
  subtitle: 'Public transport accessibility measurement',
  themes: ['transport', 'central', 'equity'],
  tagline: 'Every national accessibility measure assumes buses run to timetable. Real-time open data proves they do not — and the places that suffer most are scored as well connected.',
  status: 'The gap the Connectivity Tool concedes in its own documentation',

  problem: [
    'The Department for Transport discontinued Journey Time Statistics in March 2025, concluding there was "not a sufficient business case to continue production." The last data year was 2019. But it did not leave a vacuum — it shipped the <strong>Connectivity Tool Lite</strong>, free, covering England and Wales across roughly 15 million 100m grid squares, six travel purposes and four modes. That is a serious public tool, and any proposal claiming the government publishes nothing here is wrong.',
    'The gap is narrower and much sharper than "no accessibility statistic". It is stated in the tool’s own documentation: the model <strong>"assumes that all timetables are adhered to… will make areas with unreliable services appear more connected than they are."</strong> It also excludes fares and congestion, and rests on travel behaviour data from <strong>2011–2020</strong> that does not capture post-pandemic change.',
    'So the official measure systematically flatters exactly the places that are worst served. A neighbourhood with an hourly bus that arrives two times in three scores identically to one where it always arrives. Unreliability is invisible by construction, and it is concentrated in the same areas as deprivation and low car ownership.',
    'The consequences are not abstract. Bus journeys outside London fell from <strong>4.6 billion in 2009 to 3.6 billion in 2024</strong>, a 21.7% reduction; more than <strong>10,500 services were withdrawn between 2019 and 2024</strong>; and CPRE finds <strong>56% of small towns in the South West and North East</strong> are transport deserts or at risk of becoming one.',
    'What makes the fix newly possible is that the Bus Open Data Service is legally mandated and publishes <strong>real-time vehicle positions</strong> alongside timetables from 250+ operators. The difference between the two is measurable, continuously, at national scale — and nobody is measuring it.'
  ],

  solution: [
    'Waypoint rebuilds genuine door-to-service journey time measurement from Bus Open Data timetables, and then does what the discontinued statistic never could: recomputes continuously rather than annually.',
    'That single change transforms the product. Under the old regime a route withdrawal became visible in a statistic published up to two years later. With mandated open timetable data, a withdrawal shows up as a measured accessibility loss within days — and Waypoint publishes the delta: which neighbourhoods lost access to which class of service this quarter, and how many people live there.',
    'It layers the 2025 deprivation indices to produce a defensible, published definition of a transport desert tied to deprivation and car availability, replacing the ad-hoc definitions currently in circulation with something a minister can quote and a council can plan against.',
    'It is also the analysis that mayoral authorities currently buy from consultants to build bus franchising business cases. Building it once as a public asset removes a recurring cost from every authority pursuing franchising under the Bus Services Act.'
  ],

  datasets: [
    ['Bus Open Data Service (BODS)', 'DfT', 'Legally mandated timetables, fares and real-time location from 250+ operators. Obligations commenced 2021 and 2023.'],
    ['NaPTAN', 'DfT', 'National public transport access nodes — every stop in Great Britain.'],
    ['OS Open Roads', 'Ordnance Survey', 'Free network data for walk-access and interchange modelling.'],
    ['Census 2021', 'ONS', 'Population, car availability and small-area demographics. Note travel-to-work variables are pandemic-affected.'],
    ['Indices of Deprivation 2025', 'MHCLG', 'Published October 2025, replacing the 2019 indices most existing analysis still uses.'],
    ['NHS Organisation Data Service', 'NHS England', 'Hospital, GP and pharmacy locations as destinations.'],
    ['Get Information About Schools', 'DfE', 'School locations as destinations.']
  ],

  features: [
    ['True journey time surfaces', 'Door-to-service travel times by public transport at small-area level, computed from actual timetables and interchange.'],
    ['Continuous recomputation', 'Weekly rather than annual, so service changes register immediately instead of years later.'],
    ['Accessibility delta reporting', 'Which neighbourhoods lost access to which service class, and how many people live there — the headline nobody can currently produce.'],
    ['Transport desert definition', 'A published, defensible national definition tied to deprivation and car availability.'],
    ['Franchising business case pack', 'The accessibility analysis mayoral authorities currently commission from consultants, available as a public asset.'],
    ['Service class coverage', 'Access to hospitals, GPs, secondary schools, further education and employment centres measured separately, since one is not a substitute for another.'],
    ['Rural mobility evaluation', 'Before-and-after measurement for interventions such as demand-responsive transport schemes.']
  ],

  impact: [
    ['2019', 'The last data year of England’s discontinued journey time statistic'],
    ['10,500+', 'Bus services withdrawn between 2019 and 2024'],
    ['21.7%', 'Fall in bus journeys outside London, 2009 to 2024'],
    ['56%', 'Small towns in the South West and North East that are transport deserts or at risk']
  ],

  benefits: {
    government: [
      'Restores a capability DfT retired for cost reasons, at a fraction of the original cost, using data that is already mandated and free.',
      'Supports Bus Services Act implementation and the roughly £900m a year of bus funding by showing where it changes access and where it does not.',
      'Gives DWP evidence on jobcentre accessibility, which bears directly on claimant conditionality decisions.',
      'Provides the accessibility evidence base for the devolution agenda, where mayoral authorities are taking on transport powers without comparable data.'
    ],
    public: [
      'People can see, before moving or taking a job, whether they can actually reach it without a car.',
      'Communities losing services get measured evidence rather than anecdote when they challenge withdrawals.',
      'Investment targeted at the places where access is genuinely worst, rather than where lobbying is loudest.'
    ]
  },

  phases: [
    ['Routing engine', '4 months', 'Journey time computation from BODS validated against known routes and timings.'],
    ['National surfaces', '3 months', 'Small-area accessibility published for all English destinations classes.'],
    ['Delta reporting', '3 months', 'Continuous recomputation and change alerting operational.'],
    ['Authority tooling', '6 months', 'Franchising and network planning tools released to mayoral and county authorities.']
  ],

  risks: [
    ['Destination data licensing', 'Jobcentre and retail locations are the weak link; food store data of usable quality is commercial. Scope begins with health, education and employment centres where open data exists, and states coverage honestly.'],
    ['Data quality in BODS', 'Operator compliance varies. Coverage is published as a metric rather than assumed, and gaps are reported back to DfT as a by-product.'],
    ['Duplication', 'Transport for the North’s social exclusion tool covers related ground. Waypoint differentiates on continuous recomputation, change deltas and national coverage.']
  ],

  buyer: 'DfT Buses and Taxis, mayoral combined authorities, DWP, rural authorities',
  route: 'DOS7 Lot 1, with DfT and combined authority co-funding',

  sources: [
    ['Journey Time Statistics — discontinued', 'https://www.gov.uk/government/collections/journey-time-statistics'],
    ['Transport connectivity metric', 'https://www.gov.uk/government/publications/transport-connectivity-metric'],
    ['Bus Open Data Service', 'https://www.gov.uk/government/collections/bus-open-data-service'],
    ['Transport Committee: buses connecting communities', 'https://publications.parliament.uk/pa/cm5901/cmselect/cmtrans/494/report.html'],
    ['CPRE: transport deserts', 'https://www.cpre.org.uk/resources/transport-deserts-report/']
  ]
},

{
  id: 'hearth',
  num: '09',
  name: 'Hearth',
  subtitle: 'Retrofit outcome accountability',
  themes: ['climate', 'housing', 'money'],
  tagline: '£15bn to upgrade five million homes, and no public record of which properties got funded, by which scheme, at what cost, or whether it worked. 65,000 households found out the hard way.',
  status: 'Warm Homes Plan area-based delivery begins 2027/28',

  problem: [
    'The Warm Homes Plan commits <strong>£15bn</strong> to upgrade <strong>up to 5 million homes</strong> and lift <strong>up to 1 million families out of fuel poverty by 2030</strong>. The private rented sector must reach EPC band C by October 2030. Area-based delivery begins in 2027/28, tied to local energy plans.',
    'There is no unified eligibility framework behind it. Households are reached through separate scheme-specific routes, and ECO Flex still depends on individual councils issuing their own declarations — producing roughly three hundred inconsistent eligibility regimes for a single national objective.',
    'The targeting data is weaker than it looks. Energy Performance Certificates only cover properties transacted since 2008, so <strong>a large share of the housing stock has no certificate at all</strong>; scores are modelled rather than measured; and certificates last ten years, so many are stale. Nobody can currently target the un-certificated half of the stock.',
    'The absence of outcome verification has already produced a scandal. Around <strong>65,000 households</strong> received solid wall insulation under recent schemes; <strong>39 businesses were suspended</strong> and Ofgem was ordered to check every installation and write to all affected households. Defects included missing ventilation and exposed insulation. That failure surfaced through complaints, not data — because nothing checks whether an installed measure produced the predicted saving. Government has since said the scheme responsible was <strong>"the source of the majority of poor-quality installations."</strong>',
    'The plan has a budget and no data plan. Searching the published Warm Homes Plan for <code>data sharing</code>, <code>data matching</code>, <code>DWP</code>, <code>HMRC</code> and <code>Digital Economy Act</code> returns <strong>zero hits in every case</strong>. Its only targeting commitment is hedged as a "potential opportunity", with no legal gateway named, no timeline and no funding line.',
    'Worse, the legal plumbing points at the wrong actor. The data-sharing gateway that makes household-level targeting lawful was built to push government data <strong>to energy suppliers</strong>, so they could deliver supplier obligations. Those obligations are being abolished — one scheme ended in March 2026, the other ends <strong>31 December 2026, with no successor</strong>. Delivery moves to local authorities and a new agency, and <strong>local authorities have no equivalent route to benefits data</strong>. The current eligibility checker is a self-service funnel relying on <strong>self-declared income</strong>, which government concedes <strong>"will sometimes tell users they are ineligible when they are eligible."</strong>',
    'And the evidence base is fracturing beneath all of it. Certificates lost their primary key in March 2026 — government states plainly that <strong>"it is not possible to link certificate numbers to the former LMK_KEY"</strong> — the headline rating is replaced by four separate metrics from the second half of 2027, and the underlying calculation engine is being replaced too. Three discontinuities in a single programme.',
    'Meanwhile <strong>2.7 million households in England are in fuel poverty</strong>, the aggregate gap is £1.11bn, and cold and damp housing costs the NHS an estimated £900m a year.'
  ],

  solution: [
    'Hearth is deliberately not a targeting tool. Targeting requires household income and benefits data that cannot lawfully be published, so it belongs to councils and scheme administrators who hold it — and commercial products already serve them, at £20,000 to £80,000 a year. Building a public rival to those would duplicate a served market and run into a legal wall.',
    'What nobody does is hold the programme to account for its outcomes. Hearth tracks post-installation certificate re-lodgement against the uplift each measure predicted, by measure type, by scheme and by installer. Underperformance surfaces as a signal within months rather than as a scandal after 65,000 installations.',
    'It publishes the spend-to-outcome record: which areas received investment under which scheme, at what cost per property, and what measured improvement followed. That is the record a public accounts committee needs and cannot currently obtain, and it exists nowhere for a £15bn programme.',
    'It also fills a genuine data gap that helps everyone including the commercial tools — imputing energy performance for the substantial share of stock with no certificate, published openly with explicit uncertainty. Properties that have not been sold since 2008 are currently invisible to every scheme, which means the programme systematically misses homes for reasons that have nothing to do with need.',
    'Throughout, modelled and measured values are flagged distinctly. A system that hides the weakness of its own inputs is how £15bn gets spent on the wrong houses and reported as a success.'
  ],

  datasets: [
    ['EPC Open Data', 'MHCLG', 'Bulk download and API. Partial stock coverage, modelled scores, ten-year validity — limitations Hearth models rather than ignores.'],
    ['Indices of Deprivation 2025', 'MHCLG', 'Published October 2025. Most existing retrofit targeting still runs on the 2019 indices.'],
    ['Sub-regional fuel poverty', 'DESNZ', 'Small-area fuel poverty estimates — the key targeting layer, openly published.'],
    ['Council tax base and bands', 'MHCLG / VOA', 'Proxy for property size and value where certificate data is absent.'],
    ['Census 2021 housing', 'ONS', 'Tenure, occupancy, heating type and household composition.'],
    ['UPRN / OS Open UPRN', 'Ordnance Survey', 'Free property identifier for linking across all of the above.'],
    ['Local Area Energy Plans', 'Combined authorities', 'The delivery geography for area-based rollout from 2027/28.']
  ],

  features: [
    ['National priority score', 'One auditable ranking at property level, replacing inconsistent local eligibility declarations.'],
    ['Certificate imputation', 'Modelled performance for un-certificated stock, with published uncertainty — reaching properties currently invisible to every scheme.'],
    ['Outcome verification', 'Post-install re-lodgement tracked against predicted uplift, by measure and installer.'],
    ['Installer quality signal', 'Systematic underperformance surfaced early, from data rather than complaints.'],
    ['Area-based planning', 'Street and neighbourhood-level targeting aligned to the 2027/28 delivery model and local energy plans.'],
    ['Landlord compliance tracking', 'Progress toward the October 2030 private rented sector requirement, by area and portfolio.'],
    ['Confidence flags', 'Modelled versus measured status shown on every property, so decisions are made with their uncertainty visible.']
  ],

  impact: [
    ['£15bn', 'Warm Homes Plan investment to 2030'],
    ['5 million', 'Homes to be upgraded — requiring knowing which ones'],
    ['65,000', 'Households with solid wall insulation now requiring inspection after quality failures'],
    ['2.7m', 'Households in fuel poverty in England']
  ],

  benefits: {
    government: [
      'Gives DESNZ a defensible basis for allocating £15bn against a stated target of one million households, which requires identifying which households.',
      'Supports Ofgem’s scheme administration and remediation with the outcome data that would have caught the insulation failures early.',
      'Replaces three hundred inconsistent ECO Flex regimes with a single auditable framework, while preserving local override.',
      'Provides the property-level evidence base the area-based delivery model needs before it starts in 2027/28.'
    ],
    public: [
      'Help reaches the coldest, poorest homes rather than the homes that happen to have a recent certificate.',
      'Households are protected from botched installations by verification that operates continuously rather than after a scandal.',
      'Lower bills and warmer homes, with measurable reductions in cold-related illness.'
    ]
  },

  phases: [
    ['Data foundation', '4 months', 'Property-level linkage of certificates, deprivation, fuel poverty and tenure at national scale.'],
    ['Imputation model', '5 months', 'Performance imputation for un-certificated stock, validated against held-out certificates.'],
    ['Verification loop', '4 months', 'Outcome tracking operational with a pilot scheme administrator.'],
    ['Area-based rollout', '9 months', 'Deployed with combined authorities ahead of the 2027/28 delivery model.']
  ],

  risks: [
    ['Imputation error', 'Wrongly imputed performance means wrongly targeted spend. Published accuracy, conservative thresholds, and imputation never used alone to deny support.'],
    ['Certificate coverage', 'The underlying gap is structural and Hearth mitigates rather than solves it. Coverage is stated openly on every output.'],
    ['Privacy', 'Property-level energy and deprivation data is sensitive in combination. Public outputs are aggregated; property-level access is restricted to the delivery bodies with a lawful basis.']
  ],

  buyer: 'DESNZ Warm Homes directorate, Ofgem, combined authorities, social landlords',
  route: 'DOS7 Lot 1, with DESNZ Warm Homes programme funding',

  sources: [
    ['Warm Homes Plan', 'https://www.gov.uk/government/publications/warm-homes-plan/warm-homes-plan-html'],
    ['English Indices of Deprivation 2025', 'https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025/english-indices-of-deprivation-2025-statistical-release'],
    ['Fuel poverty statistics collection', 'https://www.gov.uk/government/collections/fuel-poverty-statistics'],
    ['Action taken to protect households with poor quality insulation', 'https://www.gov.uk/government/news/action-taken-to-protect-households-with-poor-quality-insulation'],
    ['EPC open data service', 'https://get-energy-performance-data.communities.gov.uk/']
  ]
},

{
  id: 'junction',
  num: '10',
  name: 'Junction',
  subtitle: 'Unified grid connection queue intelligence',
  themes: ['climate', 'operations', 'central'],
  tagline: 'The transmission queue is genuinely open. Four of six distribution operators return zero rows to anonymous users, and the only national view is six months stale and named “test”.',
  status: 'Gate 2 offers being issued through to March 2027',

  problem: [
    'Britain reordered its grid connection queue. The old queue exceeded <strong>700 GW</strong> — roughly four times what is needed by 2030. The reformed pipeline published in December 2025 is <strong>381.5 GW</strong>, with over <strong>300 GW removed</strong>. Offers are being issued now and are running <strong>2.5 to 5.5 months late</strong>, continuing into March 2027.',
    'The transmission side of this is a genuine open data success. The Transmission Entry Capacity register is published twice weekly as CSV with an unauthenticated API — 2,205 project rows, retrievable in a single call, no registration.',
    'Distribution is the opposite. Of six distribution network operator groups, <strong>four return zero rows to anonymous clients</strong>: their portals require login, their APIs refuse access, and CSV exports return a header row and nothing else. One publishes a monthly spreadsheet. Only one is genuinely open. This is the majority of projects by count.',
    'The only national aggregation is worse than the parts. It combines all six operators, but it was <strong>last updated six months ago</strong> while every constituent register has refreshed since, it is described as a custom view, and its dataset identifier is literally <code>ecr_manual_combine_test</code>. Its connection queue field — the single most relevant column — reads <strong>"Data Not Available" for 92.5% of its 20,075 records</strong>.',
    'The joins are broken too. The transmission register carries <strong>no geocoding of any kind</strong> — the only location field is a free-text substation name. There is <strong>no shared identifier</strong> between transmission and distribution registers, so a project appearing in both cannot be reconciled except by fuzzy matching. And the reform status column is <strong>empty for 63% of transmission projects</strong>, because it only populates after agreements are countersigned.'
  ],

  solution: [
    'Junction builds the national connection picture that neither government nor the market currently provides. It normalises all six distribution registers plus the transmission register into one schema, resolves entities across them, and maintains the join that does not exist.',
    'It geocodes the transmission queue by building and maintaining the substation gazetteer that the register lacks, turning free-text substation names into mappable locations — the single missing ingredient that prevents anyone from seeing where queue pressure actually sits.',
    'It normalises headroom to a single stated definition. The real barrier between operators is not file format but definitional inconsistency: each defines available capacity differently and publishes it as a picture rather than as data. Junction states its assumptions and applies them uniformly.',
    'And it tracks queue integrity through the reform. With Gate 2 having reordered everything and offers running months late, monitoring which projects hold capacity against which are actually progressing is both newly possible and politically salient — including the protected projects where the regulator has already refused the system operator relief.'
  ],

  datasets: [
    ['Transmission Entry Capacity register', 'NESO', 'CSV plus unauthenticated CKAN API, twice weekly. 2,205 rows. No geocoding, reform status 63% empty.'],
    ['Embedded Capacity Registers', 'Six DNO groups', 'Mandated under DCUSA with a common ENA schema — but published across four platforms, four of six login-gated.'],
    ['Interconnector register', 'NESO', 'Open CSV, 33 rows, same schema family as transmission.'],
    ['Connections reform results', 'NESO', 'Existing Agreement Register and zonal breakdowns — published as unversioned spreadsheets off a web page, not as datasets.'],
    ['Grid Supply Point boundaries', 'NESO', 'Coarse GSP polygons; newest file dates from January 2025.'],
    ['Clean Power 2030 Action Plan', 'DESNZ', 'Zonal capacity ranges by technology, the basis for strategic alignment decisions.'],
    ['Local Area Energy Plans', 'Combined authorities', 'The demand-side counterpart that currently cannot obtain consistent grid data.']
  ],

  features: [
    ['Cross-register entity resolution', 'The transmission-to-distribution join that no shared identifier provides, with match confidence published.'],
    ['Substation gazetteer', 'Free-text connection sites resolved to coordinates, making the transmission queue mappable for the first time.'],
    ['Normalised headroom', 'One stated definition of available capacity applied across all operators, with assumptions published rather than buried.'],
    ['Queue integrity tracking', 'Which projects hold capacity versus which are progressing, through the Gate 2 reordering and the offer backlog.'],
    ['Capacity discovery', 'A direct answer to the question the market cannot currently answer: where can this much capacity connect, and by when.'],
    ['Demand-side matching', 'Data centres, depots and electrolysers matched to genuine headroom — necessary because zonal pricing was rejected, so no market price signal performs this function.'],
    ['Data quality reporting', 'Coverage, staleness and completeness published as first-class metrics and fed back to operators and the regulator.']
  ],

  impact: [
    ['700 → 381.5 GW', 'Queue capacity before and after reform'],
    ['4 of 6', 'Distribution operators returning zero rows to anonymous users'],
    ['92.5%', 'National register records whose queue status reads “Data Not Available”'],
    ['2.5–5.5 months', 'Current slippage in issuing Gate 2 offers']
  ],

  benefits: {
    government: [
      'Gives the system operator and the regulator a single view of a queue currently visible only in fragments across seven publishers.',
      'Supports the digitalisation and data best practice regime that already obliges network operators to publish this data usefully.',
      'Serves combined authorities producing local area energy plans, who currently cannot obtain consistent grid data at all.',
      'Because zonal pricing was rejected, locational efficiency must now be delivered informationally rather than through price — which makes transparent capacity data more valuable, not less.'
    ],
    public: [
      'Faster connection of clean generation means lower constraint costs, which reach households through bills.',
      'Communities can see what is queued to connect near them, currently almost impossible below transmission level.',
      'Smaller developers gain the visibility that only well-resourced firms can currently buy through consultancy.'
    ]
  },

  phases: [
    ['Transmission foundation', '3 months', 'Full ingest of the open registers plus substation gazetteer construction and geocoding.'],
    ['Distribution normalisation', '5 months', 'All six embedded capacity registers ingested and normalised, with access arrangements agreed where portals are gated.'],
    ['Cross-register resolution', '4 months', 'Entity matching between transmission and distribution, with published confidence.'],
    ['Capacity discovery service', '6 months', 'Public interface and authority tooling released.']
  ],

  risks: [
    ['Access gating', 'Four operators do not serve anonymous clients. Registration appears to be free but is unconfirmed, and gated access breaks unattended pipelines. Resolving this with the regulator is a precondition, not an afterthought — and is itself a worthwhile policy outcome.'],
    ['Entity resolution accuracy', 'Without a shared key, matching is probabilistic. Confidence is published per match and low-confidence links are never silently merged.'],
    ['Moving target', 'The reform is mid-flight with offers issuing into 2027. Junction is designed to track a changing queue rather than describe a static one.']
  ],

  buyer: 'NESO, Ofgem, DESNZ Clean Power 2030, combined authorities',
  route: 'SBRI for entity resolution and gazetteer, then G-Cloud 15 for the service',

  sources: [
    ['NESO connections reform results', 'https://www.neso.energy/industry-information/connections-reform/connections-reform-results'],
    ['NESO connections reform timeline', 'https://www.neso.energy/industry-information/connections-reform/connections-reform-timeline'],
    ['Ofgem decision: connections reform package TM04+', 'https://www.ofgem.gov.uk/decision/decision-connections-reform-package-tm04'],
    ['ENA connections data dashboard', 'https://www.energynetworks.org/industry/connecting-to-the-networks/connections-data'],
    ['Clean Power 2030 Action Plan', 'https://www.gov.uk/government/publications/clean-power-2030-action-plan']
  ]
}

];
