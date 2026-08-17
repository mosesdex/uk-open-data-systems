// Two worked examples per Groundtruth system, plus the overarching case.
export default {

  overall: {
    heading: 'One problem, thirteen times',
    body: [
      'Read the twenty-six examples below and the same sentence appears in every one: <em>the record exists, but it cannot be joined to anything.</em>',
      'The Environment Agency knows it objected to an application. It does not know where. A ministry knows a developer owes £1.49bn. It cannot say for which sites. A council knows a company runs its care homes. It cannot see the other eleven councils that depend on the same company. A regulator knows spills fell 35%. It cannot say how much of that was rain.',
      'None of these is a missing dataset. Every one is a <strong>missing join</strong> — and there are only two of them. Resolve a place. Resolve an organisation.',
      'That is why thirteen systems are one platform rather than thirteen products. The hard part is not the flood analysis, the procurement analysis or the care analysis; each of those is straightforward once the data lines up. The hard part is making the data line up, and it is the <em>same</em> hard part every time.',
      'Build the two resolutions once as open infrastructure and thirteen questions that cannot currently be answered become answerable — then they compound, because a single event reaches several systems at once and each new system costs less than the last.'
    ]
  },

  bySystem: {

    sentinel: [
      { problem: 'Three companies bid for a £4m council contract. Two of them share a director. Nobody notices, because neither record carries a company number and the buyer has no way to check.',
        solution: 'Sentinel resolves all three bidders to companies, reads the directorship graph from the free ownership register, and flags the competition as connected — before award, not after an investigation.' },
      { problem: 'A framework worth £200m produces 400 call-offs across dozens of authorities. Six suppliers win most of them. No single buyer sees the pattern, because each call-off is one record in one authority.',
        solution: 'Sentinel reads the related-processes field, aggregates call-offs back to the parent framework, and surfaces the concentration — the most tractable collusion signal available in UK data.' }
    ],

    compass: [
      { problem: 'A county forecasts falling pupil numbers and closes a specialist unit. Two years later demand in one district has risen sharply and children are placed forty miles away at roughly £65,000 a place.',
        solution: 'Compass forecasts at planning area rather than county level, showing the district rising while the county falls — the mismatch the National Audit Office found in two-thirds of councils.' },
      { problem: 'A council must submit a SEND reform plan to unlock its share of a £5bn deficit write-off. It cannot evidence where demand will sit in three years, so the plan is assertion rather than analysis.',
        solution: 'Compass produces the demand projection and specialist place requirement the plan needs, from published statistics with no case data involved.' }
    ],

    plumbline: [
      { problem: 'A council reports 91% of major applications decided on time and is judged compliant. Measured against the actual statutory deadline it is 19%, because more than three-quarters used an agreed extension.',
        solution: 'Plumbline reports both numbers side by side, every time, and tracks extension usage as a first-class metric rather than a footnote.' },
      { problem: 'The Housing Delivery Test that triggers presumption-in-favour sanctions was last measured on data ending March 2023. Councils and the department are both flying blind on the mechanism meant to deliver 1.5 million homes.',
        solution: 'Plumbline maintains a continuous delivery estimate between official measurements, so the trajectory is visible rather than discovered two years late.' }
    ],

    highwater: [
      { problem: 'The Environment Agency objects to 47 homes on flood risk grounds. The council approves them anyway. The Agency never learns the outcome — one of 7,011 cases where it does not know what was decided.',
        solution: 'Highwater recovers the decision from the authority’s own published record and closes the gap, producing the compliance figure the Agency’s sampling approach cannot.' },
      { problem: 'A journalist asks how many homes were built in flood zones against expert advice. Nobody can answer, because the objections file carries no address, postcode or coordinate.',
        solution: 'Highwater resolves each objection to a site, joins it to the flood map, and answers the question — the analysis an insurer currently supplies to Parliament using paid data.' }
    ],

    catchment: [
      { problem: 'A council with falling rolls closes a primary school. Two miles away another is over capacity and turning children away. Both facts are true, and neither is visible in council-level statistics.',
        solution: 'Catchment publishes the 3,651 planning area boundaries and shows surplus and shortage side by side inside the same authority.' },
      { problem: 'Basic Need capital is allocated at planning area and year group with no offsetting between areas — so £1.096bn is distributed on a geography that is published nowhere and cannot be mapped.',
        solution: 'Catchment reconstructs the geography from the school membership table the department already publishes, and releases it openly.' }
    ],

    junction: [
      { problem: 'A developer asks where they can connect 5MW within two years. Two network operators both report "available capacity" — computed on incompatible bases, because the specification delegates the calculation to each of them.',
        solution: 'Junction normalises to one stated definition and publishes each operator’s own method alongside it, so the numbers can finally be compared.' },
      { problem: 'The same project appears in both the transmission and distribution registers under different identifiers, with no shared key. Counting either register alone is wrong; counting both double-counts.',
        solution: 'Junction resolves projects across registers with match confidence published per link, and never silently merges a low-confidence match.' }
    ],

    ledger: [
      { problem: 'A community was promised a school alongside a 400-home development. Six years on there is no school, and nobody can show whether the money was collected, spent, or is still sitting.',
        solution: 'Ledger attaches the contribution to the site and reads the received and spent status the schema already carries but nothing currently reads spatially.' },
      { problem: 'A council holds around £19m of unspent developer contributions and is asked publicly why. It cannot produce a spatial account of what was promised, for what, and where.',
        solution: 'Ledger maps every recorded obligation by council, ward, site and purpose — making £1.49bn visible for the first time.' }
    ],

    bellwether: [
      { problem: 'A care operator running more than two-thirds of one borough’s care home beds gets into difficulty. The council finds out when it reaches the news.',
        solution: 'Bellwether computes that concentration continuously from the regulator’s own published register, where 93.9% of beds already carry a company identifier.' },
      { problem: 'A children’s home group appears in the register under three slightly different owner names, so its true size is invisible — and statute now requires geographical concentration to be assessed.',
        solution: 'Bellwether resolves the name variants to one organisation. The same correction raises the largest special school group from an apparent 30 schools to its real 51.' }
    ],

    sightline: [
      { problem: 'Active Travel England advised on planning applications covering 521,000 homes in a single year and published none of it. Government is now cutting consultee involvement by around 40%, with no data on what that advice achieved.',
        solution: 'Sightline builds the outcome record — what was advised, what was decided, what was built — giving the reform an evidence base before it is enacted.' },
      { problem: 'A council overrides expert advice on a development. Residents want to know whether that is unusual. No published source can tell them.',
        solution: 'Sightline publishes override rates with context — including the finding that the rate has been flat for nine years even as the raw counts rose.' }
    ],

    lastmile: [
      { problem: 'A family buys a new-build and discovers there is no gigabit connection and none planned. Building regulations have required every new home to be built connectable since 2022, and nobody checks.',
        solution: 'Lastmile joins new homes to property-level connectivity status and produces the compliance picture that has never existed for that duty.' },
      { problem: 'Public subsidy is targeted at premises that new development has already made commercially viable, because the intervention list and the development pipeline are never compared.',
        solution: 'Lastmile surfaces the overlap, so subsidy goes where commercial build genuinely will not reach.' }
    ],

    bulwark: [
      { problem: 'A flood defence fails. The council needs to know who was responsible for maintaining it. The national record says "Unknown" — as it does for 73.7% of 141,629 assets.',
        solution: 'Bulwark resolves each asset to the land parcel beneath it and the parcel to a registered organisation, distinguishing genuinely unowned from merely unrecorded.' },
      { problem: 'Maintenance is prioritised using a national condition figure quoted as though it covered the estate. It is computed on the quarter of assets that have a condition grade at all.',
        solution: 'Bulwark publishes coverage alongside every statistic, and flags assets whose next inspection date has already passed.' }
    ],

    watchman: [
      { problem: 'A supplier enters administration on a Friday afternoon. Which departments, councils and services depend on it? Nobody can say before Monday, and possibly not for weeks.',
        solution: 'Watchman reads the notice — which carries a structured company number — and lists every public dependency immediately, with no name matching required.' },
      { problem: 'A small supplier files accounts late two years running and takes on new charges over its assets. Both are published signals of difficulty. Nobody is watching, because the standard financial models need profit data small companies never file.',
        solution: 'Watchman treats those as events rather than inputs to a prediction, and alerts the buyers who depend on that supplier.' }
    ],

    baseline: [
      { problem: 'Spills fell 35% in a year the Environment Agency itself describes as drier than average. A regulator being stood up now must decide whether £22.1bn of investment is working, and has no weather-adjusted figure to judge it by.',
        solution: 'Baseline normalises spill behaviour against actual local rainfall from 1,044 free monitoring stations, separating the investment effect from the weather.' },
      { problem: 'An overflow’s recorded spill count halves — because its monitor was offline for four months. The improvement is an artefact, and the published figure does not say so.',
        solution: 'Baseline reports monitor availability alongside every spill count, so an unwatched overflow is never mistaken for a quiet one.' }
    ]

  }
};
