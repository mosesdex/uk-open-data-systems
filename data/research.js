// Findings from the access audit of 17 August 2026. Consumed by build.js.
export default {
  date: '17 August 2026',
  intro: [
    'The binding constraint on this platform is not modelling skill or computing power. It is <strong>access</strong>. A source that needs an account cannot be part of Groundtruth, because the whole proposition is that a government body can reproduce every number without asking anyone&rsquo;s permission.',
    'So the research began by testing access rather than by reading documentation. 101 endpoints were probed from a clean client &mdash; no account, no key, no subscription, no cookie. <strong>69 returned HTTP 200.</strong> Everything downstream follows from that result.'
  ],

  headline: [
    ['69', 'of 101 endpoints returned data to an anonymous request'],
    ['0', 'accounts, keys or subscriptions needed'],
    ['96.5%', 'of open schools already carry a property reference'],
    ['45.4%', 'carry an organisation identifier &mdash; the gap']
  ],

  findings: [
    {
      n: '01',
      title: 'The place spine is free, and needs no registration',
      lede: 'This is the single most important finding in the study.',
      body: [
        'Ordnance Survey documentation steers you to the OS Data Hub, which wants an account. The downloads path does not. A range request against it returned <span class="mono">HTTP 206</span> and real archive bytes with no key of any kind.',
        'That releases the entire free portfolio &mdash; including OS Open UPRN and, critically, <strong>OS Open Linked Identifiers</strong>, which is exactly the property-to-street-to-topographic crosswalk the place spine needs.'
      ],
      note: 'The earlier working assumption &mdash; that the place spine required a licensed addressing product &mdash; was wrong for the identifier layer. The licensing line still holds for addresses, which is why Groundtruth emits identifiers and never address strings.',
      table: {
        head: ['Product', 'Format', 'Size', 'Role'],
        rows: [
          ['OS Open UPRN', 'CSV', '618.5 MB', 'Every property reference in GB, with coordinates'],
          ['OS Open Linked Identifiers', 'CSV', '672.0 MB', 'The crosswalk: property &harr; street &harr; topographic'],
          ['OS Open USRN', 'GeoPackage', '296.9 MB', 'Street references'],
          ['OS Open TOID', 'CSV', '1.4 MB', 'Topographic identifiers'],
          ['Code-Point Open', 'CSV', '14.5 MB', 'Postcode centroids'],
          ['OS Open Names', 'CSV', '103.3 MB', 'Place and street gazetteer'],
          ['Boundary-Line', 'Shapefile', '736.9 MB', 'Administrative boundaries'],
          ['OS Open Roads', 'Shapefile', '606.1 MB', 'Road network']
        ]
      }
    },
    {
      n: '02',
      title: 'Grid connection data is far more open than the sector says',
      lede: 'Four of the six network operators publish through a full query API, anonymously.',
      body: [
        'UK Power Networks, SP Energy Networks, Northern Powergrid and Electricity North West each expose an Opendatasoft catalogue with filtering, aggregation and geospatial querying. UK Power Networks alone publishes 137 datasets, including its embedded capacity register.',
        'This corrects the premise Junction was built on. The gap is <em>not</em> access. The gap is that each operator computes &ldquo;available capacity&rdquo; on its own basis, so the published numbers cannot be compared with each other.'
      ]
    },
    {
      n: '03',
      title: 'The flood asset register is reachable, with condition data',
      lede: 'A direct upgrade to Bulwark.',
      body: [
        'The Environment Agency asset-management interface answers anonymously and carries condition, last inspection date, asset type, primary purpose and protection type per asset.',
        'That means the overdue-inspection question and the coverage-qualified condition statistic can both be answered today, rather than being a future ambition.'
      ]
    },
    {
      n: '04',
      title: 'Some sources described as open are not',
      lede: 'The trap case, and the reason the audit was worth running.',
      body: [
        'The energy performance register returns <span class="mono">HTTP 200</span> to an anonymous client &mdash; and serves a sign-in page. A system built on documentation alone would have shipped with a dependency that silently returns nothing.',
        'It was removed rather than assumed to work. Lastmile now uses Price Paid Data, which carries a new-build flag at address level and is genuinely open.'
      ]
    }
  ],

  baseline: {
    heading: 'The thesis, measured',
    lede: 'Computed from the full school register on 17 August 2026 &mdash; 52,486 establishments, of which 27,167 are open.',
    rows: [
      ['Open schools', '27,167', 'The denominator', ''],
      ['Carrying a property reference', '96.5%', 'The <em>where</em> link is nearly solved here', 'ok'],
      ['Carrying coordinates', '97.7%', '', 'ok'],
      ['Carrying an organisation identifier', '45.4%', 'The <em>who</em> link is barely half solved', 'warn'],
      ['Total capacity', '9,928,858', 'places', ''],
      ['Pupils on roll', '8,857,132', '', ''],
      ['National utilisation', '89.2%', '', ''],
      ['Distinct academy trusts', '2,185', 'Largest runs 96 schools', '']
    ],
    close: 'This is the whole argument in one table. In the dataset with the best identifier hygiene in UK government, <em>where</em> is 96.5% solved and <em>who</em> is 45.4% solved. Most datasets are far worse on both.'
  },

  mismatch: {
    heading: 'A finding worth stating plainly',
    body: [
      'Joining those authorities to the national boundary set by name matched <strong>152 of 316</strong> districts.',
      'The thirty that fail are two-tier counties &mdash; Kent, Lancashire, Hampshire, Essex, Surrey, Norfolk, Staffordshire and others &mdash; whose schools are planned across several districts at once.',
      'That is not a data-cleaning nuisance. It is exactly the defect Catchment exists to fix: school planning happens on a geography that is published nowhere and does not line up with the administrative geography everything else uses. The prototype shows this on click rather than papering over it.'
    ]
  },

  blocked: {
    heading: 'What failed, and why it stays visible',
    lede: 'A system that quietly drops a source it cannot reach is a system whose coverage figures cannot be trusted. These are published in the platform&rsquo;s own console.',
    rows: [
      ['Care regulator syndication', '401', 'Needs a key. The published location file is still free &mdash; use that.'],
      ['Charity register interface', '401', 'Needs a key. Bulk extracts remain downloadable.'],
      ['Bus open data service', '401', 'Needs a free account &mdash; still excluded by the rule.'],
      ['Energy performance register', '200', 'Serves a sign-in page anonymously. Replaced by Price Paid Data.'],
      ['Communications coverage data', '403', 'Blocks automated retrieval; needs a manual step.'],
      ['School register download page', '403', 'Page blocks automation &mdash; but the underlying file is directly reachable.'],
      ['Benefits statistics interface', '503', 'Account required.'],
      ['Local land charges search', '403', 'Search service blocks automation.']
    ]
  },

  cannot: {
    heading: 'What free data cannot do',
    items: [
      ['Bid prices', 'Never published in UK procurement data. This kills the entire family of price-based collusion tests, so Sentinel relies on structural signals instead &mdash; shared directors, shared owners, framework concentration.'],
      ['Active travel casework', 'Held in a structured system covering over 2,000 responses a year, and published nowhere. Sightline cannot use it until it is released.'],
      ['Energy certificate tracking', 'Not reachable without signing in, so it cannot serve as the national completion signal.'],
      ['Communications coverage automation', 'Blocked to machines. Usable, but only with a manual download step.'],
      ['Anything about an individual', 'Excluded by design rather than by capability. Compass forecasts from published aggregates and touches no personal record.']
    ],
    close: 'The ceiling is set by what government chooses to publish, not by what can be computed. Groundtruth&rsquo;s proposition is that the published material already supports far more than is currently extracted from it &mdash; because the two joins that would unlock it have never been built.'
  },

  rules: {
    heading: 'Rules that follow from the evidence',
    items: [
      ['Emit identifiers, never addresses', 'Keeps the platform inside the licensing line permanently.'],
      ['Publish a confidence score on every match', 'Nothing merges silently. Low-confidence links go to a human queue.'],
      ['Ship every statistic with its coverage', '&ldquo;73.7% unknown&rdquo; is a finding, not something to hide.'],
      ['Record every source&rsquo;s access status', 'A source that starts failing must show as failing, not quietly produce a smaller number.'],
      ['Stay reproducible', 'Same inputs, same commit, same outputs &mdash; because a government buyer will eventually be challenged on a number by a named company.']
    ]
  }
};
