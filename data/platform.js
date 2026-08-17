// Groundtruth — the unified platform. Consumed by build.js.
export default {
  name: 'Groundtruth',
  tagline: 'Five products. Two joins. One platform.',
  standfirst: 'Every system Dexter DCL can deliver today fails at the same two joins — resolving <em>places</em> and resolving <em>organisations</em>. Build those once as public infrastructure and the five products stop being five builds.',

  thesis: [
    'The ten proposals in this portfolio were developed independently. Researching their implementation revealed something none of them showed on its own: they break in the same two places.',
    'The Environment Agency cannot map its own flood objections because the dataset carries no spatial reference. Councils receive school capacity data at a geography whose boundaries are published nowhere. The housing delivery mechanism runs on a measurement three years stale. An insurer, not government, supplies Parliament with evidence on floodplain housebuilding — because the join required a paid Ordnance Survey field. Every one of those is the same missing asset: <strong>a national, resolved record of where development happens</strong>.',
    'On the other side, procurement supplier records resolve inconsistently to company numbers, grid connection registers share no key between transmission and distribution, council spending data carries no company identifiers at all, and there is <strong>no canonical register of UK public sector organisations</strong> — the one that existed was decommissioned and its domains no longer resolve.',
    'Groundtruth builds those two resolution layers as open infrastructure, then runs the five products on top. The products are the revenue. The spines are the moat.'
  ],

  spines: [
    {
      id: 'place',
      name: 'The place spine',
      role: 'Resolves development to canonical spatial identifiers',
      problem: 'England has no open, national, site-level record of where homes are permitted and built. The Ministry’s own planning application dataset holds 100,627 records from four contributing councils — effectively three, since two are a shared service — and its collection has not run since <strong>17 September 2025</strong>, while every other dataset on the platform collected yesterday. The April 2026 planning data regulations mandate three things: local plan timetables, minerals and waste timetables, and housing requirement figures. <strong>Planning applications are not among them.</strong>',
      builds: [
        ['Planning reference resolution', 'Authority planning references resolved to site location and property identifier, across the fragmented estate of council portals.'],
        ['Completion signal', 'New-build energy certificates as the address-level, near-real-time completion proxy — the only national one that exists. Keyed on report type, which distinguishes new build from existing stock.'],
        ['Pupil planning area geography', 'The 3,651 planning areas reconstructed from the school membership table the Department already publishes, with a back-series to 2012/13.'],
        ['Substation gazetteer', 'Free-text connection site names resolved to coordinates, making the grid queue mappable.']
      ],
      constraint: 'Ordnance Survey’s agreement permits publishing <em>identifiers</em> appended to your own data. It prohibits publishing address strings or coordinates derived from its address products. Groundtruth therefore emits a resolution index — reference to identifier — and lets consumers join to the free identifier file themselves. That is the only architecture that is unambiguously publishable, and it has to be designed in from the start.',
      gotchas: [
        'The free identifier file carries <strong>no status field</strong>. Its 41.6 million records match the licensed product’s entire property table, which means plots with planning permission, occupied houses and demolished buildings are all present and <strong>indistinguishable</strong>. Anyone treating it as a list of real dwellings is wrong.',
        'The successor table that should record splits and merges is <strong>empty nationally — zero records</strong>. When a house converts into flats, the old identifier goes historical and new ones appear with no machine-readable link between them. Lineage has to be inferred.',
        'Status changed meaning in 2025. It now records whether street naming is complete, not whether the building exists — that moved to a separate field. Any time series spanning 2024 to 2026 contains an artefactual shift.',
        'Publication lag is measurable at <strong>34 to 76 days</strong>. The lag before that — from a house existing to a council recording it — has no service level, no target, and no published measurement anywhere.'
      ]
    },
    {
      id: 'entity',
      name: 'The entity spine',
      role: 'Resolves organisations to canonical identifiers across registers',
      problem: 'The identifier that actually persists across UK public sector systems is not the company number. It is the <strong>Public Procurement Organisation Number</strong>, introduced by the Procurement Act — because it exists for councils, NHS trusts and unincorporated bodies that have no company number, and because the debarment list is keyed on it. Meanwhile the register of UK public sector organisations that government built has been decommissioned; its domains fail to resolve at all.',
      builds: [
        ['Procurement number to company number', 'The mapping between the Procurement Act’s organisation number and Companies House, which nothing currently publishes.'],
        ['Public sector organisation register', 'Reconstructed from the central government organisations interface — which carries stable identifiers and, unusually, machine-readable succession chains — plus health, education and charity registers.'],
        ['Beneficial ownership graph', 'The full persons-with-significant-control register is a free daily bulk download. That is the graph backbone at zero API cost.'],
        ['Directorship graph', 'Seeded from organisations that actually appear in the data rather than the whole register, then expanded — roughly 100,000 calls for 20,000 seeds, inside one day’s rate limit.']
      ],
      constraint: 'Succession is the hard part, and it is about to get harder: 134 councils merge into 38 unitary authorities on 1 April 2028. Area codes and organisational identity diverge precisely at a merger, so an entity spine that conflates the two will break exactly when it is most needed.'
    }
  ],

  matrix: {
    head: ['System', 'Place spine', 'Entity spine', 'What it needs that nothing else provides'],
    rows: [
      ['Catchment', true, false, 'Planning area geography and small-area completions'],
      ['Highwater', true, false, 'Objection records resolved to sites and flood zones'],
      ['Plumbline', true, false, 'Completion signal faster than annual statistics'],
      ['Sentinel', false, true, 'Organisation resolution and the corporate graph'],
      ['Junction', true, true, 'Substation locations and cross-register project matching']
    ]
  },

  buildable: {
    now: [
      ['Pupil planning area geography', 'Every input is open and published. 20,426 school-to-area assignments verified, matching the Department’s own count of 3,651 exactly. Coordinates present for 99.9% of relevant schools. No freedom of information request, no scraping.'],
      ['Honest planning performance measurement', 'Both figures are already published side by side — 91% of major applications decided "in time", 19% within the actual statutory deadline. The product is presentation, not extraction. Extension usage is published too: 43% of all decisions, 77% of majors.'],
      ['Procurement process indicators', 'The corruption risk indicators that need no bid prices — procedure type, whether a call for tenders was published, submission and decision periods, supplier concentration.'],
      ['Framework call-off concentration', 'The related-processes field genuinely works, making this the most tractable collusion signal available in UK data.'],
      ['Beneficial ownership graph', 'Free daily bulk download of the full persons-with-significant-control register.'],
      ['Flood objection archive and trend', 'The objections dataset parses cleanly. The 30% unknown-outcome gap and the flat rate behind rising counts are both publishable findings on day one.'],
      ['The address lag nobody measures', 'How long between a home existing and its identifier appearing? The publication half is documented at 34 to 76 days. The council half is unmeasured by anyone — and measurable by joining energy certificate or land registry dates to property identifiers. A cheap, original, publishable statistic that no institution currently produces.']
    ],
    blocked: [
      ['Individual bid prices', 'Not published in UK procurement data at any point. This eliminates the entire statistical screen family the academic literature is built on, and four of the standard collusion indicators. Design around it rather than hoping.'],
      ['Small-area internal migration', 'Nothing exists below local authority level. The detailed origin-destination series was discontinued in 2020. Must be synthesised, and the synthesis must be labelled as such.'],
      ['National planning application data', 'Not mandated, specification still a working draft, platform dataset a three-council alpha with dead collection. This is a multi-year gap, not a near-term one — which is precisely why the place spine has value.'],
      ['Record-level building control completions', 'The data exists and feeds the official statistics. It is never published below aggregate.'],
      ['Address text at scale', 'Locked behind Ordnance Survey and Royal Mail licensing. The energy certificate register is the only open route to an identifier-to-address link, and it covers roughly half the housing stock.']
    ]
  },

  sequence: [
    ['Publish the planning area geography', 'Months 1–3', 'Open, unpaid, under an open licence. It is weeks of work, demonstrably missing, and it converts an unknown supplier into the people who fixed something government wanted fixed. The named team that owns the survey is the buyer for everything after.'],
    ['Ship Catchment on top of it', 'Months 3–9', 'Small-area demand forecasting and the surplus-shortage adjacency map. The National Audit Office has already written the thesis: national projections are accurate, the failure is spatial.'],
    ['Build the entity spine and Sentinel', 'Months 6–15', 'Organisation resolution first, then process indicators and framework concentration. Route findings through the compliance service, which is open to anyone, rather than the review service, which is not.'],
    ['Extend the place spine to Highwater and Plumbline', 'Months 12–24', 'Both consume the same asset. Two further buyers in two further departments, at marginal cost.'],
    ['Junction last', 'Months 18–30', 'It needs both spines mature, and four of six network operators must first be persuaded to serve data to anonymous clients.']
  ],

  honesty: [
    'The place spine depends on resolving planning references across roughly 400 council portals. That is the exact failure mode which killed the original planning alerts project in 2011 and is currently degrading its volunteer successor — which has lost 20-plus councils to bot protection since June 2026 and has authorities frozen as far back as January 2019. Any plan that treats this as solved is wrong. Coverage must be published as a metric, not assumed.',
    'Groundtruth cannot be built on a public sector contractor licence. That instrument permits using address data for one named client’s purposes, prohibits commercial exploitation of any product incorporating the results, and requires destruction within 30 days. A multi-client product needs a partner licence or the addressing agreement that exists by name in Ordnance Survey’s own template and is published nowhere. <strong>Resolve this before writing code, not after.</strong>',
    'Two independent measurements of supplier identifier coverage in procurement data disagree — roughly 65% missing when counting company numbers on supplier records only, roughly 8% when counting the Procurement Act organisation number across all parties. Both were measured against the live feed. The discrepancy is itself the finding: the identifier exists, but not where most consumers look for it.'
  ]
};
