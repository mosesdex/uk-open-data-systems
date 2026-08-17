// Systems 11–17. The Groundtruth extension. Consumed by build.js.
export default [

{
  id: 'ledger',
  num: '11',
  name: 'Ledger',
  subtitle: 'Developer contributions, made mappable',
  themes: ['housing', 'local', 'money'],
  tagline: 'The Ministry’s own schema holds £1.49bn of developer obligations. Not one record has a location. The property identifier field is populated in 0.0% of planning applications; the address field, in the same records, is populated in 98.1%.',
  status: 'Schema designed, unpopulated',

  problem: [
    'When housebuilders get permission, they pay councils for the schools, roads and affordable housing the development will need. These are Section 106 agreements, and the money is enormous. Roughly <strong>£9bn sits unspent</strong> across English councils, including about <strong>£817m of affordable housing money — some 11,000 homes</strong> — with one London borough holding over £250m.',
    'The Ministry already runs a national schema for this. It holds <strong>39,325 contribution records totalling £1,491,818,575</strong>, models purposes from affordable housing to education to highways, and even tracks whether money has been received or spent. Councils are being asked publicly why the money is sitting there.',
    'Every one of those 39,325 records has <strong>zero geometry</strong>. Not sparse — none. And the reason traces to one field: in the linked planning application dataset, the <strong>property identifier is populated in 0.0% of 100,627 records</strong>, while the free-text address field is populated in <strong>98.1%</strong>.',
    'That single contrast is the whole argument. The Ministry has already agreed the identifier belongs there. It cannot fill it. Coverage compounds the problem — 67 of roughly 330 authorities publish agreements, and 4 publish applications.'
  ],

  solution: [
    'Ledger resolves the addresses that exist into the identifiers that do not, then attaches contributions to sites. The moment that join is made, £1.49bn of recorded obligations becomes mappable for the first time — by council, by ward, by development, by purpose.',
    'It then answers the question councils are actually being asked: what was promised, what was received, what was spent, and what is sitting. The schema already carries funding status; nothing currently reads it spatially.',
    'It also fixes the identity problem underneath. Agreements link to authority-local application references that are not nationally unique, so the same reference string exists in multiple councils. Resolution must be constrained by authority or the entire dataset silently mislocates.',
    'And it publishes coverage as a headline metric rather than a footnote. A national picture built from a fifth of authorities is useful only if it says so.'
  ],

  datasets: [
    ['Developer agreement contributions', 'MHCLG', '39,325 records, £1.49bn, purpose-coded. Open licence, live API. No geometry on any record.'],
    ['Developer agreement transactions', 'MHCLG', '49,891 records carrying received and spent status — the promised-versus-delivered signal, already modelled.'],
    ['Planning applications', 'MHCLG', '100,627 records. Address text 98.1% populated, property identifier 0.0%. Four contributing authorities.'],
    ['Infrastructure funding statements', 'MHCLG', '236 records from 172 authorities — but each is a link to a PDF, not data.'],
    ['Title boundaries', 'HM Land Registry via MHCLG', '8,220,990 polygons republished under an open licence. Keyed on a spatial identifier, not a title number.'],
    ['New-build energy certificates', 'MHCLG', 'Address-level completion signal, for testing whether contributed-for development actually happened.']
  ],

  features: [
    ['Address-to-identifier resolution', 'The 98,713 free-text addresses converted into property identifiers — the specific gap the Ministry cannot close itself.'],
    ['Contribution mapping', 'Every recorded obligation placed, by council, ward and site.'],
    ['Promised versus delivered', 'Received and spent status read spatially, answering the question councils are being asked publicly.'],
    ['Purpose analysis', 'Affordable housing, education, transport, open space and monitoring fees separated and compared across authorities.'],
    ['Authority-constrained matching', 'Application references resolved within their own authority, because the same reference exists in several.'],
    ['Coverage reporting', 'Which authorities publish, which do not, and what share of England the picture actually represents.'],
    ['Standards feedback', 'Resolution failures reported back to the Ministry as data-quality defects, improving the source.']
  ],

  impact: [
    ['£1.49bn', 'Recorded contributions currently carrying no location at all'],
    ['0.0% / 98.1%', 'Property identifier versus address field population in the same records'],
    ['~£9bn', 'Developer contributions estimated unspent across English councils'],
    ['67 of ~330', 'Authorities publishing agreements to the national schema']
  ],

  benefits: {
    government: [
      'Answers the unspent-contributions question spatially for the first time, for a Ministry already under pressure on it.',
      'Fills a field the Ministry designed and cannot populate, improving its own platform rather than competing with it.',
      'Gives councils an audit position on money they hold — an average of roughly £19m each is a real liability.',
      'Produces the evidence base for whether developer contributions are delivering the infrastructure they were collected for.'
    ],
    public: [
      'Communities can see what was promised for a development near them, and whether it arrived.',
      'Affordable housing money that has sat unspent becomes visible and therefore accountable.',
      'Councils under scrutiny can demonstrate where money has gone rather than being unable to answer.'
    ]
  },

  phases: [
    ['Resolve and map', '3 months', 'Address resolution across the published application set, with match confidence reported per record.'],
    ['Contribution layer', '3 months', 'Obligations attached to sites and published by council and purpose.'],
    ['Delivery tracking', '4 months', 'Received and spent status surfaced, with the unspent position by authority.'],
    ['Coverage campaign', 'ongoing', 'Work with non-publishing authorities to raise coverage from a fifth toward national.']
  ],

  risks: [
    ['Coverage, not capability', 'The limiting factor is that most authorities do not publish. Ledger can resolve everything published and must state plainly how much of England that represents.'],
    ['Reference collisions', 'Authority-local references are not nationally unique. Matching must be constrained by authority; failing to do so produces confidently wrong output.'],
    ['Political sensitivity', 'Mapping unspent money names councils. Reporting presents context — money is often legitimately committed but not yet drawn — rather than a naked league table.']
  ],

  buyer: 'MHCLG Digital Planning, individual planning authorities, the Home Builders Federation',
  route: 'DOS7 Lot 1, aligned to the planning data standards programme',

  sources: [
    ['Planning Data Platform — developer agreement contributions', 'https://www.planning.data.gov.uk/dataset/developer-agreement-contribution'],
    ['Planning Data Platform — planning applications', 'https://www.planning.data.gov.uk/dataset/planning-application'],
    ['Infrastructure funding statement dataset', 'https://www.planning.data.gov.uk/dataset/infrastructure-funding-statement'],
    ['Planning Data Platform dataset index', 'https://www.planning.data.gov.uk/dataset/'],
    ['Title boundary dataset', 'https://www.planning.data.gov.uk/dataset/title-boundary']
  ]
},

{
  id: 'bellwether',
  num: '12',
  name: 'Bellwether',
  subtitle: 'Provider concentration and failure exposure',
  themes: ['children', 'local', 'money'],
  tagline: 'Parliament made computing this a statutory function in July 2026 — and the register deliberately withholds the company number needed to do it.',
  status: 'Statutory duty live since 15 July 2026',

  problem: [
    'Councils buy care from companies. When a large operator collapses, councils discover their exposure afterwards. The care home sector has done this twice at national scale, and each time the state absorbed the consequences.',
    'The data to see it coming mostly exists. The adult social care regulator publishes <strong>57,009 active locations</strong> with a Companies House number attached to <strong>91.1% of care home locations and 93.9% of beds</strong>. That is enough to compute, today, which councils depend on which operators. Measured directly: <strong>40 council-and-company pairs where one company runs more than 15% of an area’s care home beds</strong>, including one London borough at <strong>67.4%</strong>.',
    'Children’s social care is where it becomes urgent. The <strong>Children’s Wellbeing and Schools Act 2026 came into force on 15 July 2026</strong>, and its financial oversight provision sets out how to decide which providers get monitored. The criteria include <strong>"the geographical concentration of those establishments or agencies"</strong> and <strong>"the share of any market within England"</strong>. Somebody now has a legal duty to compute exactly this.',
    'And the children’s register <strong>publishes owner names but no company numbers</strong>. The same is true of independent special schools, where the identifier field exists and is populated in 13 of 52,486 records. Measured consequence: naive name counting <strong>understates the largest special school group by 70%</strong> — 30 schools where the real figure is 51 — because the same owner appears as three different strings.'
  ],

  solution: [
    'Bellwether resolves care providers to canonical organisations across three registers, then computes concentration and exposure at council level.',
    'Where the regulator already publishes a company number, the join is direct — that covers most of adult social care. Where it does not, resolution is the product: matching owner names to companies through the corporate graph, handling the variants that defeat simple normalisation, and publishing match confidence rather than asserting certainty.',
    'It then produces the exposure view: for each council, which operators hold what share of local capacity, and for each operator, how many councils depend on it and how concentrated that dependency is. One operator in the data runs over four thousand beds across only twelve councils — a very different risk shape from one running more beds across fifty-seven.',
    'Financial distress signals attach on top, drawn from insolvency notices, charges and overdue filings rather than from accounting ratios, for reasons set out under risks.'
  ],

  datasets: [
    ['Active locations register', 'Care Quality Commission', '57,009 locations, 122 fields. Carries company number, charity number, bed counts, council and coordinates. Free, no key.'],
    ['Children’s social care providers', 'Ofsted', 'Provider-level data with owner name at 99.4%, places and sector. No company number. Home names and addresses redacted.'],
    ['Schools register', 'DfE', 'Independent special schools with proprietor name at 100%, capacity and pupil counts. Company number field effectively empty.'],
    ['Academy trust membership', 'DfE', 'Company number on 100% of open trusts — the cleanest identifier join available in the sector.'],
    ['Companies House bulk and streams', 'Companies House', 'Company data, persons of significant control, charges and insolvency. Free.'],
    ['Insolvency notices', 'The Gazette', 'Free JSON interface, over three million notices, each carrying a structured company number.'],
    ['Registered provider list', 'Regulator of Social Housing', 'Corporate form field routes each provider to the correct identifier authority — under half are Companies House entities.']
  ],

  features: [
    ['Council exposure map', 'For every council, which operators hold what share of local capacity — the analysis the new statutory criteria describe.'],
    ['Operator concentration profile', 'For every operator, how many councils depend on it and how tightly, distinguishing broad from concentrated footprints.'],
    ['Name resolution across variants', 'The specific failure that understates the largest special school group by 70%, corrected and measured.'],
    ['Dual registration handling', 'Care home records registered twice during ownership transfer inflate national bed counts by 6.4% if counted naively. Deduplicated, with the flag respected.'],
    ['Mixed-authority identifiers', 'Roughly 2.5% of published identifiers are not Companies House numbers at all but mutual society, royal charter or charity references. Routed to the correct register rather than failing silently.'],
    ['Event-based distress signals', 'Insolvency notices, charge filings, strike-off action and overdue accounts — observable for every company regardless of size.'],
    ['Statutory oversight pack', 'Concentration and market share computed to the criteria now written into law.']
  ],

  impact: [
    ['93.9%', 'Care home beds already carrying a resolvable company identifier'],
    ['67.4%', 'Share of one London borough’s care home beds run by a single company'],
    ['15 July 2026', 'Date the statutory financial oversight duty came into force'],
    ['70%', 'Understatement of the largest special school group under naive name counting']
  ],

  benefits: {
    government: [
      'Supplies the concentration and market share analysis that the new financial oversight criteria explicitly require.',
      'Gives adult social care market oversight a council-level exposure view rather than a provider-level one.',
      'Lets councils see their own dependency before an operator fails rather than after.',
      'Corrects a measurement error that materially understates consolidation in the special school market.'
    ],
    public: [
      'Fewer people moved at short notice when a care operator collapses, because the exposure was visible in advance.',
      'Transparency over who owns the providers delivering publicly funded care to children and vulnerable adults.',
      'Better-targeted regulation of a market where the competition authority has already found margins well above competitive levels.'
    ]
  },

  phases: [
    ['Adult social care first', '3 months', 'Where identifiers already exist, the exposure map is buildable immediately at high coverage.'],
    ['Children’s resolution', '5 months', 'Owner names resolved to companies, with confidence published, against the statutory criteria.'],
    ['Special schools', '3 months', 'Proprietor resolution and the corrected concentration picture.'],
    ['Distress signals', '4 months', 'Event-based early warning attached across all three sectors.']
  ],

  risks: [
    ['Financial models do not work here', 'The standard corporate failure ratios depend on profit and loss data that small companies do not file — roughly two-thirds of the model’s power is unavailable. Published tests also show such models flagging around a quarter of all companies, of which the overwhelming majority never fail. Bellwether uses event signals and treats any score as triage, never as a prediction of failure.'],
    ['Capacity is not commissioned volume', 'A bed in one council may be occupied by someone placed by another, and self-funded beds are not council exposure at all. Bellwether measures physical capacity by location and says so — the commissioning layer is not in open data.'],
    ['Property structures are invisible', 'Both historic care home collapses ran through the property and lease side, not the operating company. The regulator registers only the operator. Group structure must be reconstructed, and some of it cannot be.'],
    ['Naming a company as at risk', 'Publication could itself precipitate difficulty. Concentration is published; distress scoring stays in a restricted tier for oversight bodies.']
  ],

  buyer: 'DfE children’s social care, DHSC and CQC market oversight, ADASS, individual councils',
  route: 'SBRI for the resolution engine, then DOS7 for the oversight service',

  sources: [
    ['CQC data and HSCA active locations', 'https://www.cqc.org.uk/about-us/transparency/using-cqc-data'],
    ['Children’s Wellbeing and Schools Act 2026', 'https://www.legislation.gov.uk/ukpga/2026/21/contents'],
    ['Children’s social care in England 2026', 'https://www.gov.uk/government/statistics/childrens-social-care-in-england-2026'],
    ['CMA children’s social care market study', 'https://assets.publishing.service.gov.uk/media/6228726cd3bf7f158c844f65/Final_report.pdf'],
    ['The Gazette data services', 'https://www.thegazette.co.uk/data']
  ]
},

{
  id: 'sightline',
  num: '13',
  name: 'Sightline',
  subtitle: 'Statutory consultee advice, and what happened to it',
  themes: ['housing', 'central', 'operations'],
  tagline: 'Active Travel England advised on 2,045 planning applications covering 521,000 homes last year. It published none of it. Government is reforming statutory consultees using almost no data on what they achieve.',
  status: 'Consultee reform consulted on, January 2026',

  problem: [
    'Certain expert bodies must be consulted on planning applications. They give advice, councils decide, and almost none of that advice is published as data.',
    'Active Travel England became a statutory consultee in 2023. In 2025-26 it <strong>responded to 2,045 consultations covering more than 521,000 homes</strong> and recommended improvements on applications comprising <strong>191,000 homes</strong>. It holds every one of these in a casework system. Of its 79 publications, exactly two are transparency releases and both concern funding. Even its council capability ratings are published as a PDF.',
    'Its own independent reviewer recommended creating a framework to record outcomes — meaning the body was not systematically tracking what happened to its advice, let alone publishing it.',
    'The Environment Agency shows the other failure mode. It <strong>does</strong> publish flood objections at application level — <strong>23,336 records across 426 authorities</strong>, including 633 where permission was granted against its advice, covering 347,425 homes. But the file carries <strong>no location of any kind</strong>, and for 7,011 records the Agency does not know what the council decided. Published and unmappable.',
    'Meanwhile government consulted through January 2026 on cutting statutory consultee involvement by around 40%. A reform premised on consultee burden, conducted with essentially no public data on consultee outcomes.'
  ],

  solution: [
    'Sightline builds the outcome layer for statutory consultee advice: what was advised, what was decided, and what was built.',
    'It starts with the Environment Agency data because it is already published and needs only resolution — the objections become mappable, the unknown outcomes get recovered, and the compliance picture becomes checkable rather than asserted.',
    'It then extends the same template to Active Travel England. The casework exists in a structured system; the ask is publication, not creation. A working demonstration on flood data is the strongest possible argument for it.',
    'And it gives the consultee reform an evidence base. If the case for cutting consultee involvement is that it delays development without improving it, that is a testable claim — and nobody can currently test it.'
  ],

  datasets: [
    ['Flood risk objections', 'Environment Agency', '23,336 records, 426 authorities, open licence. No spatial reference. Outcome unknown for 30%.'],
    ['Water quality objections', 'Environment Agency', 'A second, smaller sheet in the same file with an objection reason field — largely untouched.'],
    ['Active Travel England casework', 'ATE', 'Over 2,000 responses a year covering 521,000 homes. Held in a structured system, published nowhere.'],
    ['Planning applications', 'MHCLG and authority portals', 'The decisions that consultee advice was given on.'],
    ['Flood zones', 'Environment Agency', 'Open geospatial services with no key required — the layer objections need joining to.'],
    ['New-build energy certificates', 'MHCLG', 'Whether advised-against development was actually completed and occupied.']
  ],

  features: [
    ['Advice-to-outcome chain', 'Consultee advice resolved to a site, joined to the decision, and followed through to completion.'],
    ['Outcome recovery', 'The 7,011 cases where the Environment Agency does not know what the council decided.'],
    ['Override analysis', 'Which authorities grant against expert advice, in what circumstances, and with what context — housing pressure, viability, defence status.'],
    ['Reform evidence', 'Whether consultee involvement changes outcomes, which is the premise of the reform now under way.'],
    ['Publication template', 'A worked demonstration of what a consultee outcome dataset looks like, usable by any consultee body.'],
    ['Versioned archive', 'Each annual release preserved, since the source silently restates history and the reform may break the series entirely.'],
    ['Coverage metric', 'Resolution coverage published rather than assumed.']
  ],

  impact: [
    ['2,045', 'Active Travel England consultations last year, none published as data'],
    ['521,000', 'Homes covered by that advice'],
    ['7,011', 'Flood objections where the Agency does not know the outcome'],
    ['~40%', 'Proposed reduction in consultee involvement, consulted on with no outcome data']
  ],

  benefits: {
    government: [
      'Gives the consultee reform the evidence base it currently lacks, before the reform is enacted.',
      'Lets consultee bodies demonstrate their own value, which they presently cannot.',
      'Supplies the Environment Agency with the outcome data its own sampling approach cannot produce.',
      'Creates a reusable publication template for every statutory consultee, not just two.'
    ],
    public: [
      'Communities can see whether expert advice about a development near them was followed.',
      'The trade-off between development speed and expert scrutiny becomes measurable rather than asserted.',
      'Bodies giving advice on public safety become accountable for whether it lands.'
    ]
  },

  phases: [
    ['Flood objections', '4 months', 'Resolve, map and archive the already-published dataset. Publish the recovered compliance figure.'],
    ['Outcome recovery', '4 months', 'Close the unknown-outcome gap and report the corrected national position.'],
    ['Template and advocacy', '4 months', 'Publish the consultee outcome specification and take it to Active Travel England.'],
    ['Second consultee', '6 months', 'Extend to active travel casework, subject to publication being agreed.']
  ],

  risks: [
    ['Publication is a decision, not a build', 'The active travel half depends on a body agreeing to publish. The flood half does not, which is why it comes first and carries the argument.'],
    ['The series may break', 'Consultee reform proposes removing objections in some circumstances, which would discontinue the only national indicator. The archive makes that break visible rather than invisible.'],
    ['Contested framing', 'Authorities will object to being ranked on overrides. Context is reported alongside, and the finding that the override rate has been flat for nine years is published as prominently as the rising counts.']
  ],

  buyer: 'Environment Agency, Active Travel England, MHCLG Planning, Defra',
  route: 'SBRI for resolution and recovery, then DOS7 for the service',

  sources: [
    ['EA objections to planning on the basis of flood risk', 'https://www.gov.uk/government/publications/environment-agency-objections-to-planning-on-the-basis-of-flood-risk'],
    ['Active Travel England annual report and accounts', 'https://www.gov.uk/government/publications/active-travel-england-annual-report-and-accounts-2025-to-2026'],
    ['Reforms to the statutory consultee system', 'https://www.gov.uk/government/consultations/reforms-to-the-statutory-consultee-system'],
    ['Active Travel England planning guidance', 'https://www.activetravelengland.gov.uk/planning'],
    ['Flood map for planning', 'https://environment.data.gov.uk/']
  ]
},

{
  id: 'lastmile',
  num: '14',
  name: 'Lastmile',
  subtitle: 'Connectivity at new homes',
  themes: ['housing', 'central', 'equity'],
  tagline: 'Every new home has been required to be gigabit-ready since 2022. No compliance data is published anywhere. The only person tracking it nationally is one independent analyst.',
  status: 'Regulation in force, unmonitored',

  problem: [
    'Building Regulations have required gigabit-ready infrastructure in new dwellings in England since December 2022, with a cost cap per dwelling and a connectivity plan required alongside the building notice. Scotland and Wales followed.',
    '<strong>There is no published compliance dataset.</strong> A regulation with a per-dwelling duty, a cost cap and a plan requirement, and no monitoring data at all.',
    'The raw material to check it is free and unusually good. The broadband subsidy programme publishes property-level data — every record carrying a property identifier, a status flag, and the contracted supplier where one exists. A status of "White" means no gigabit infrastructure and none expected within three years. It refreshes every four months.',
    'The regulator computes coverage per premises, using a licensed address product, and then <strong>publishes it aggregated to postcode</strong>. In mixed postcodes — common in rural areas and on new estates — knowing 83% of a postcode has gigabit tells you nothing about a specific house.',
    'So the property-level truth exists on the subsidy side, the property-level truth is computed and discarded on the coverage side, and the compliance question nobody is asking is entirely property-shaped.'
  ],

  solution: [
    'Lastmile joins property-level gigabit status to newly completed homes, and answers the question the regulation implies but nobody monitors: are new homes actually being built connectable, and are they being connected?',
    'The subsidy dataset supplies one side of the join for free, already keyed on property identifiers. The other side — which properties are new homes — comes from new-build energy certificates, which carry the same identifier and a field distinguishing new build from existing stock.',
    'That produces a national compliance picture at property level: new homes in areas with no gigabit infrastructure, new homes in subsidy intervention areas, and new developments where connectivity was planned but not delivered.',
    'It also flags the inverse, which matters for public money: subsidised interventions targeting premises that new development has already made commercially viable.'
  ],

  datasets: [
    ['Open market review premises data', 'Building Digital UK', 'Property-level gigabit status with subsidy classification, contracted supplier and delivery date. Free, open licence, refreshed every four months. England and Wales.'],
    ['Connected Nations', 'Ofcom', 'Coverage at postcode for fixed and 100-metre grid for mobile. Free and open — computed per premises, published aggregated.'],
    ['New-build energy certificates', 'MHCLG', 'Property identifier plus a report type field distinguishing new build from existing stock.'],
    ['Open property identifiers', 'Ordnance Survey', 'The free identifier file, 41.6 million records. Carries no status field, so cannot distinguish a plot from a house.'],
    ['Linked identifiers', 'Ordnance Survey', 'The free crosswalk between property, street and topographic identifiers.'],
    ['Planning applications', 'MHCLG and authority portals', 'Development pipeline, for forward-looking connectivity planning.']
  ],

  features: [
    ['New-build connectivity compliance', 'Whether homes completed under the gigabit-readiness duty are in areas with gigabit infrastructure.'],
    ['Property-level notspot mapping', 'Premises with no gigabit and none expected, joined to development pipeline.'],
    ['Subsidy efficiency check', 'Interventions targeting premises that development has already made commercially viable.'],
    ['Developer performance', 'Connectivity outcomes by developer and by authority, which no published source currently allows.'],
    ['Forward pipeline', 'Permitted but unbuilt development matched against planned network build.'],
    ['Coverage disaggregation', 'The postcode-level published picture reconciled against property-level subsidy data, exposing mixed postcodes.'],
    ['Devolved coverage gap', 'Scotland and Northern Ireland publish separately; the national picture is assembled rather than assumed.']
  ],

  impact: [
    ['Dec 2022', 'Gigabit-readiness duty in force for every new English dwelling'],
    ['0', 'Published datasets on compliance with it'],
    ['4 months', 'Refresh cycle of the free property-level subsidy data'],
    ['1', 'People tracking new-build connectivity nationally, independently']
  ],

  benefits: {
    government: [
      'Creates the compliance evidence base for a building regulation that has run unmonitored since 2022.',
      'Improves subsidy targeting by identifying interventions overtaken by commercial development.',
      'Gives the broadband programme a development-aware view rather than a static premises view.',
      'Supports building control and planning authorities enforcing a duty they currently cannot check.'
    ],
    public: [
      'Buyers of new homes can see connectivity status before purchase rather than after moving in.',
      'Households in genuine notspots become visible individually rather than averaged into a postcode.',
      'Public subsidy targeted where commercial build genuinely will not reach.'
    ]
  },

  phases: [
    ['Join and baseline', '3 months', 'Subsidy data joined to new-build certificates, national baseline published.'],
    ['Compliance picture', '3 months', 'New-home connectivity status by authority and developer.'],
    ['Subsidy efficiency', '3 months', 'Overlap analysis delivered to the broadband programme.'],
    ['Pipeline view', '6 months', 'Forward development matched to planned network build.']
  ],

  risks: [
    ['Certificates are a proxy, not a register', 'New-build certificates indicate completion, imperfectly and with an undocumented lag. That lag must be measured empirically before any latency claim is made.'],
    ['Coverage is not connection', 'Infrastructure passing a property is not the same as a working service in the home. The data supports the former; claims must not overreach into the latter.'],
    ['Geographic scope', 'The property-level subsidy data covers England and Wales. Scotland and Northern Ireland publish separately and must be assembled, not assumed.']
  ],

  buyer: 'Building Digital UK, DCMS, building control authorities, network operators',
  route: 'G-Cloud for the service, with broadband programme funding',

  sources: [
    ['Open market review and premises in BDUK plans', 'https://www.gov.uk/government/publications/january-2026-omr-and-premises-in-bduk-plans-england-and-wales'],
    ['Property-level release user guide', 'https://www.gov.uk/government/publications/may-2025-omr-and-premises-in-bduk-plans-england-and-wales/uprn-level-release-user-guide-and-technical-note-for-premises-in-bduk-plans'],
    ['Ofcom Connected Nations data downloads', 'https://www.ofcom.org.uk/phones-and-broadband/coverage-and-speeds/data-downloads2'],
    ['Energy performance data service', 'https://get-energy-performance-data.communities.gov.uk/'],
    ['OS Open UPRN', 'https://www.ordnancesurvey.co.uk/products/os-open-uprn']
  ]
},

{
  id: 'freehold',
  num: '15',
  name: 'Freehold',
  subtitle: 'Land ownership resolution',
  themes: ['money', 'central', 'housing'],
  tagline: 'Free ownership data on one side. Free boundary geometry on the other. The key that joins them is a paid product. The paywall sits precisely in the middle.',
  status: 'Government committed to free release during 2026',

  problem: [
    'You can find out, for free, which companies own land in England and Wales. You can also download, for free, <strong>8,220,990 land parcel boundaries</strong> under an open licence. What you cannot do is connect the two.',
    'The ownership data is keyed on title numbers. The free boundaries are keyed on a different spatial identifier. The crosswalk between them is a paid product. Free data on both sides, paywall exactly in the middle.',
    'The government has committed to changing this. The Land Use Framework, published March 2026, states it will work with the registry <strong>"this year"</strong> to provide <strong>"free, spatial land ownership data for larger properties covering the vast majority of England and Wales, excluding almost all homeowners."</strong>',
    'Two things make that commitment worth watching rather than waiting on. No size threshold is defined. And <strong>the registry’s own business plan does not mention the commitment at all</strong> — it commits instead to adding identifiers to more free datasets and to "initial design work" on more clearly identifying the parties recorded on the register.',
    'That last phrase is the entity spine problem, stated by the registry itself, and still at design stage. Roughly <strong>10% of land in England remains unregistered</strong> despite compulsory registration since 1990.'
  ],

  solution: [
    'Freehold builds the resolution layer between land, boundaries and organisations — the join that free data on both sides currently cannot make.',
    'On the spatial side it resolves parcels to properties and to the identifiers that other datasets use, so land can be joined to development, flood risk, contributions and everything else in the platform.',
    'On the organisational side it resolves the parties named on ownership records to canonical organisations, connecting land to the corporate graph. That is what turns a list of owners into an answer to who actually controls what.',
    'And it is positioned for the commitment landing. If free spatial ownership data is published during 2026, whoever already has a working resolution layer has a large head start. If it slips, the resolution layer is what makes the existing free data usable in the meantime — which is the stronger position either way.'
  ],

  datasets: [
    ['Title boundaries', 'HM Land Registry via MHCLG', '8,220,990 polygons under an open licence, refreshed regularly. Keyed on a spatial identifier, not a title number.'],
    ['UK companies that own property', 'HM Land Registry', 'Free with registration. Keyed on title number. Terms are not open-data terms.'],
    ['Overseas companies ownership data', 'HM Land Registry', 'Roughly 100,000 records, monthly, free with registration.'],
    ['Price paid data', 'HM Land Registry', 'Free and open. Transaction history at address level.'],
    ['Companies House', 'Companies House', 'The organisational side of the join, including ownership and control.'],
    ['Land use and designation layers', 'Defra and MHCLG', 'Protected sites, green belt, agricultural classification and nutrient catchments, largely open.']
  ],

  features: [
    ['Parcel-to-property resolution', 'Land boundaries connected to the property identifiers the rest of the platform uses.'],
    ['Ownership-to-organisation resolution', 'Registered parties resolved to canonical companies, connecting land to the corporate graph.'],
    ['Landholding aggregation', 'Total holdings by organisation and by group, rather than title by title.'],
    ['Corporate and overseas exposure', 'Which land is held through companies, and where control sits.'],
    ['Development pipeline linkage', 'Ownership joined to permissions, contributions and completions across the platform.'],
    ['Unregistered land mapping', 'Where the roughly 10% of unregistered land sits, which is itself unmapped.'],
    ['Commitment tracking', 'Public monitoring of whether the free spatial ownership release actually arrives during 2026.']
  ],

  impact: [
    ['8.2m', 'Land parcel boundaries free under an open licence'],
    ['~10%', 'Of English land still unregistered after 35 years of compulsory registration'],
    ['2026', 'Year the government committed to free spatial ownership data for larger properties'],
    ['0', 'Mentions of that commitment in the registry’s own business plan']
  ],

  benefits: {
    government: [
      'Delivers the practical capability behind a published land use commitment that the delivery body has not yet planned for.',
      'Supports the registry’s own stated intention to identify parties on the register more clearly.',
      'Gives land use policy a spatial view of ownership concentration, which it currently commissions rather than holds.',
      'Provides the foundation for nature markets and biodiversity requirements, both of which need to know who controls land.'
    ],
    public: [
      'Who owns land, and how much of it, becomes answerable without buying the answer.',
      'Communities can see the ownership behind development proposals in their area.',
      'The land held through offshore and corporate structures becomes visible spatially rather than only as a list.'
    ]
  },

  phases: [
    ['Spatial resolution', '4 months', 'Boundaries resolved to property identifiers, published as an open index.'],
    ['Organisational resolution', '4 months', 'Registered parties resolved to companies with confidence published.'],
    ['Aggregation and analysis', '4 months', 'Landholding by organisation and group, with corporate and overseas exposure.'],
    ['Commitment readiness', 'ongoing', 'Positioned to ingest the free spatial ownership release the moment it lands.']
  ],

  risks: [
    ['The commitment may slip', 'It is conditional on an impact assessment and absent from the delivery body’s plan. Freehold is designed to be useful without it and better with it.'],
    ['Registration terms are not open terms', 'The ownership datasets are free but gated, with terms that are not open-data terms. Redistribution rights must be established before anything derived is published.'],
    ['Identifier mismatch is the whole problem', 'Boundaries and ownership use different keys by design. Resolution is probabilistic at the margins and must publish confidence rather than assert certainty.']
  ],

  buyer: 'Defra land use, MHCLG, HM Land Registry, combined authorities',
  route: 'SBRI for resolution, then DOS7 aligned to the land use programme',

  sources: [
    ['Land Use Framework for England', 'https://www.gov.uk/government/publications/land-use-framework'],
    ['HM Land Registry business plan 2026', 'https://www.gov.uk/government/publications/hm-land-registry-business-plan-2026/hm-land-registry-business-plan-2026'],
    ['Use land and property data service', 'https://use-land-property-data.service.gov.uk/'],
    ['Title boundary dataset', 'https://www.planning.data.gov.uk/dataset/title-boundary'],
    ['Price paid data', 'https://www.gov.uk/government/collections/price-paid-data']
  ]
},

{
  id: 'bulwark',
  num: '16',
  name: 'Bulwark',
  subtitle: 'Flood defence ownership and condition',
  themes: ['climate', 'operations', 'local'],
  tagline: 'The Environment Agency cannot identify the owner of 73.7% of England’s flood defences, and has no condition grade for 75% of them. All 141,629 are geolocated and free to download.',
  status: 'Measured directly from the published data',

  problem: [
    'England has <strong>141,629 recorded flood defence assets</strong>, published free and openly with full geometry. Anyone can download them today.',
    'Two fields in that dataset describe a national failure. <strong>Asset owner reads "Unknown" on 104,439 of them — 73.7%.</strong> And <strong>current condition is blank on 106,179 — 75.0%</strong>, covering <strong>43,601 kilometres</strong> of defence.',
    'Where condition is recorded, the picture is worse than it first looks: of the 35,263 assets carrying both a current and a target grade, <strong>5,877 are below their target</strong>. But that 16.7% is computed on a quarter of the asset base. Nobody knows about the rest.',
    'A third field compounds it. Whether an asset should be reflected in the national flood map — which underpins planning decisions and insurance pricing — reads <strong>"Not Yet Considered" on 53.4%</strong> of assets. A majority of England’s flood defences have never been assessed for whether they belong in the map that governs where houses get built.',
    'The consequence is already documented. The National Audit Office found that for the lack of <strong>£34m in annual maintenance funding</strong>, more than <strong>200,000 properties</strong> were at increased flood risk — while the Agency <strong>underspent its capital programme by £310m</strong> over two years.'
  ],

  solution: [
    'Bulwark resolves flood defence assets to the land they sit on and the organisations responsible for them — which is precisely the join the Agency cannot currently make.',
    'The assets are geolocated lines. Land parcel boundaries are free and open. Property identifiers are free and open. Corporate ownership records exist. Nothing in that chain is paywalled at the point where Bulwark operates, and yet the ownership field sits empty on three-quarters of the estate.',
    'It then makes the condition gap visible rather than averaged away. A national figure computed on a quarter of assets is not a national figure, and reporting it as one obscures the problem. Bulwark publishes coverage alongside every statistic.',
    'And it surfaces the operational signals already present in the data. Asset records carry inspection histories with next-inspection dates — some of them already in the past. Overdue inspection is computable from published data and reported by nobody.'
  ],

  datasets: [
    ['Spatial flood defences', 'Environment Agency', '141,629 assets with polyline geometry and 37 fields including current and target condition, standard of protection, owner and inspection dates. Free, open, bulk.'],
    ['Asset management interface', 'Environment Agency', 'Per-asset inspection history, maintenance activities with planned versus actual dates, and condition over time.'],
    ['Title boundaries', 'HM Land Registry via MHCLG', '8.2 million parcels under an open licence — the land the assets sit on.'],
    ['Open property identifiers', 'Ordnance Survey', 'Free identifier and coordinate file for resolving assets to properties.'],
    ['Corporate and overseas ownership', 'HM Land Registry', 'Who owns the land, once parcels are resolved. Free with registration, restrictive terms.'],
    ['National flood risk assessment', 'Environment Agency', 'What the defences protect, and what happens if they fail.'],
    ['Companies House', 'Companies House', 'Resolving named owners to organisations, and detecting distress among them.']
  ],

  features: [
    ['Ownership resolution', 'Assets matched to parcels and parcels to owners — closing the 73.7% unknown-owner gap that the Agency itself reports.'],
    ['Condition coverage reporting', 'Every condition statistic published with its denominator, so a quarter-coverage figure is never presented as national.'],
    ['Overdue inspection detection', 'Next-inspection dates already in the past, computable from published data and currently reported by nobody.'],
    ['Flood map completeness', 'The 53.4% of assets never assessed for inclusion in the map that governs planning and insurance.'],
    ['Failure consequence modelling', 'What each poorly-conditioned or unowned asset protects, joined to properties at risk.'],
    ['Maintenance versus capital', 'Planned against actual maintenance activity, against the backdrop of a documented underspend.'],
    ['Third-party asset register', 'The privately owned defences — nearly 18% of the estate — identified and attributable for the first time.']
  ],

  impact: [
    ['73.7%', 'Flood defence assets whose owner the Environment Agency records as unknown'],
    ['75.0%', 'Assets with no current condition grade, covering 43,601 km'],
    ['53.4%', 'Assets never assessed for inclusion in the national flood map'],
    ['200,000', 'Properties the auditor found at increased risk for want of £34m of maintenance']
  ],

  benefits: {
    government: [
      'Closes an ownership gap the Agency reports on three-quarters of its own asset register.',
      'Lets maintenance spending be targeted at assets whose condition is actually known, and identifies where knowledge is missing.',
      'Establishes who is responsible for privately owned defences, which is unanswerable today and decisive when one fails.',
      'Supports the flood investment programme by showing where liability is being created faster than it is being maintained.'
    ],
    public: [
      'Communities can find out who is responsible for the defence protecting them.',
      'Properties relying on defences in unknown condition become visible to their owners and insurers.',
      'Maintenance money directed by evidence rather than by whichever assets happen to have been inspected.'
    ]
  },

  phases: [
    ['Baseline and gaps', '2 months', 'Full ingest, with the condition and ownership coverage gaps published as findings.'],
    ['Ownership resolution', '5 months', 'Assets resolved to parcels and owners, with match confidence published per asset.'],
    ['Inspection and condition', '3 months', 'Overdue inspections and condition trajectories surfaced to the Agency and lead local flood authorities.'],
    ['Consequence layer', '5 months', 'Failure consequence modelled against properties at risk.']
  ],

  risks: [
    ['Unknown may mean unowned', 'Some assets genuinely have no identifiable responsible party — a finding in itself, not a resolution failure. The two must be distinguished and reported separately.'],
    ['Attribution is consequential', 'Naming a private owner as responsible for a defence has legal weight. Confidence is published per match, and low-confidence attributions are never asserted.'],
    ['Condition data may be absent for good reason', 'Some assets may not warrant inspection. The product reports the gap and asks the question rather than assuming neglect.']
  ],

  buyer: 'Environment Agency, Defra, lead local flood authorities, insurers',
  route: 'SBRI for resolution, then DOS7 for the asset service',

  sources: [
    ['Spatial flood defences including standardised attributes', 'https://environment.data.gov.uk/spatialdata/spatial-flood-defences-including-standardised-attributes/wfs'],
    ['Environment Agency asset management service', 'https://environment.data.gov.uk/asset-management/'],
    ['NAO: resilience to flooding', 'https://www.nao.org.uk/reports/resilience-to-flooding/'],
    ['National assessment of flood and coastal erosion risk', 'https://www.gov.uk/government/publications/national-assessment-of-flood-and-coastal-erosion-risk-in-england-2024'],
    ['Title boundary dataset', 'https://www.planning.data.gov.uk/dataset/title-boundary']
  ]
},

{
  id: 'watchman',
  num: '17',
  name: 'Watchman',
  subtitle: 'Insolvency exposure across public suppliers',
  themes: ['fraud', 'money', 'operations'],
  tagline: 'Three million insolvency notices, free, each carrying a company number. Nobody joins them to the register of who holds public contracts.',
  status: 'Free interface, structured identifiers, unused',

  problem: [
    'When a company holding public contracts fails, the consequences land on whoever depended on it. The failure of a major government contractor in 2018 remains the defining example, and the lesson drawn afterwards was that nobody had a consolidated view of exposure.',
    'The raw material to build that view is free and better than expected. The official insolvency record publishes a <strong>JSON interface with no key required</strong>, carrying <strong>over three million notices</strong>. Critically, each notice carries a <strong>structured company number</strong> — a direct identifier join, with no name matching required.',
    'On the other side sit the public procurement record, the care provider registers, the school trust register and the social housing register — millions of contractual and regulatory relationships between the state and companies.',
    'Nobody joins them. So the question "which public contracts and regulated services are currently held by companies in insolvency proceedings" has no answer, despite both halves being free and one of them carrying a clean identifier.',
    'And the standard alternative does not work. Predicting failure from filed accounts requires profit and loss data that small companies do not publish — a requirement that was <strong>paused in January 2026 and pushed to 2028, with an opt-out from publication attached</strong>. Roughly two-thirds of the standard model’s power is unavailable, and published testing shows such models flagging around a quarter of all companies, of which the overwhelming majority never fail.'
  ],

  solution: [
    'Watchman abandons prediction and does something more useful: it watches events, and it knows who depends on whom.',
    'It ingests insolvency notices continuously, resolves each to an organisation through the entity spine, and checks that organisation against every public relationship the platform knows about — contracts, care registrations, school trusts, social housing, land holdings.',
    'The output is an exposure alert rather than a risk score. Not "this company might fail" but "this company has entered administration, and here are the seventeen contracts and four hundred care beds that depend on it."',
    'It layers earlier signals underneath — charge filings, strike-off action, overdue accounts — all observable for every company regardless of size, and all events rather than inferences.',
    'And it inverts for planning: for any council or department, which of its suppliers show distress signals, and what would be lost if each failed.'
  ],

  datasets: [
    ['Insolvency notices', 'The Gazette', 'Free JSON interface, no key, over three million notices, each with a structured company number and a direct link to the company record.'],
    ['Companies House bulk and streams', 'Companies House', 'Company data, charges, insolvency and control. Free bulk downloads plus resumable event streams.'],
    ['Procurement record', 'Cabinet Office', 'Contract awards and performance across the public sector.'],
    ['Care provider registers', 'CQC and Ofsted', 'Regulated services and their operators.'],
    ['Academy trust membership', 'DfE', 'Company numbers on every open trust.'],
    ['Registered providers', 'Regulator of Social Housing', 'Social housing providers, with a corporate form field routing each to the right identifier authority.'],
    ['Local authority spending', 'Councils', 'Payments to suppliers, once normalised and resolved.']
  ],

  features: [
    ['Event ingestion', 'Insolvency notices processed continuously, resolved to organisations by identifier rather than by name.'],
    ['Exposure alerting', 'When an organisation enters proceedings, everything the public sector depends on it for, immediately.'],
    ['Early signals', 'Charge filings, strike-off action and overdue accounts — observable for every company, including those filing minimal accounts.'],
    ['Buyer-side view', 'For any council or department, which suppliers show distress and what each failure would cost.'],
    ['Concentration risk', 'Where many public bodies depend on one organisation, or one group behind several apparent suppliers.'],
    ['Group awareness', 'Distress in a parent or sibling company that the contracting entity’s own record would not show.'],
    ['Historical validation', 'Back-tested against known failures, with performance published rather than claimed.']
  ],

  impact: [
    ['3m+', 'Insolvency notices available free, each carrying a company number'],
    ['0', 'Systems joining them to the register of public contracts'],
    ['2028', 'Earliest date small company accounts might carry profit and loss — with an opt-out attached'],
    ['~1 in 198', 'Annual company failure rate, against which any predictive model must justify itself']
  ],

  benefits: {
    government: [
      'Gives the public sector the consolidated supplier exposure view whose absence was the lesson of the 2018 contractor collapse.',
      'Works for small suppliers, where accounts-based models cannot, because it uses events rather than ratios.',
      'Supports the care market oversight duties that now sit in statute, from the supplier side.',
      'Lets buyers act before a failure rather than discovering exposure afterwards.'
    ],
    public: [
      'Services less likely to stop abruptly when a provider fails.',
      'Public money less likely to be committed to organisations already in difficulty.',
      'Transparency over which public services depend on which private companies.'
    ]
  },

  phases: [
    ['Ingest and resolve', '3 months', 'Insolvency notices flowing and resolving to organisations by identifier.'],
    ['Exposure joins', '4 months', 'Connected to procurement and provider registers across the platform.'],
    ['Early signals', '3 months', 'Charges, strike-off and filing delinquency added as leading indicators.'],
    ['Buyer tooling', '5 months', 'Council and department supplier risk views released.']
  ],

  risks: [
    ['Do not build a failure predictor', 'The base rate is roughly one in two hundred companies a year. Any model flagging a meaningful share will be wrong the overwhelming majority of the time. Watchman reports events that have happened and dependencies that exist, not probabilities of future failure.'],
    ['Reputational harm', 'Publishing that a company shows distress signals could itself precipitate difficulty. Exposure analysis stays in a restricted tier for public bodies; only aggregate concentration is published.'],
    ['Identifier gaps', 'Several provider registers carry no company number, and under half of social housing providers are Companies House entities at all. Coverage is reported per register rather than assumed uniform.']
  ],

  buyer: 'Cabinet Office commercial, Public Sector Fraud Authority, CQC and Ofsted oversight, individual councils',
  route: 'SBRI for the resolution and alerting engine, then G-Cloud for the service',

  sources: [
    ['The Gazette data services', 'https://www.thegazette.co.uk/data'],
    ['Companies House data products', 'https://www.gov.uk/guidance/companies-house-data-products'],
    ['Changes to accounts filing from April 2028', 'https://www.gov.uk/government/news/companies-house-to-bring-in-changes-to-accounts-filing-from-april-2028'],
    ['Registered providers of social housing', 'https://www.gov.uk/government/publications/current-registered-providers-of-social-housing'],
    ['CQC data and transparency', 'https://www.cqc.org.uk/about-us/transparency/using-cqc-data']
  ]
}

];
