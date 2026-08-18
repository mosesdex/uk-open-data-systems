// Two worked examples per Groundtruth system, plus the overarching case.
export default {

  overall: {
    heading: 'One problem, thirteen times',
    body: [
      'Read the twenty-six examples on the system pages and the same sentence turns up in all of them: <em>the record exists, but it cannot be matched to anything else.</em>',
      'The Environment Agency knows it objected to an application. It does not know where. A ministry knows a developer owes £1.49bn. It cannot say for which sites. A council knows a company runs its care homes. It cannot see the other eleven councils that depend on the same company. A regulator knows spills fell 35%. It cannot say how much of that was rain.',
      'None of these is a missing dataset. Every one is a <strong>missing link</strong> — and there are only two kinds. Work out <em>where</em>. Work out <em>who</em>.',
      'That is why this is one platform and not thirteen separate products. The flood work, the contracts work and the care work are each fairly simple once the data lines up. Getting it to line up is the hard bit — and it is the <em>same</em> hard bit every time.',
      'Fix those two links once, give them away, and thirteen questions nobody can currently answer become answerable. After that it snowballs: one piece of news reaches several systems at once, and every new system costs less than the one before it.'
    ]
  },

  bySystem: {

    sentinel: [
      { problem: 'Three companies bid for a £4m council contract. Two of them share a director. Nobody notices, because neither record carries a company number and the buyer has no way to check.',
        solution: 'Sentinel works out which real companies the three bidders are, sees that two of them share a director, and flags the bid as connected — before the contract is awarded, not after an investigation.' },
      { problem: 'A framework worth £200m produces 400 call-offs across dozens of authorities. Six suppliers win most of them. No single buyer sees the pattern, because each call-off is one record in one authority.',
        solution: 'Sentinel adds up every order placed under that framework across every authority, and shows that six firms are taking most of it. This is the clearest warning sign available in UK data.' }
    ],

    compass: [
      { problem: 'A county forecasts falling pupil numbers and closes a specialist unit. Two years later demand in one district has risen sharply and children are placed forty miles away at roughly £65,000 a place.',
        solution: 'Compass forecasts neighbourhood by neighbourhood instead of county-wide, so the rising district shows up even while the county falls. The National Audit Office found this mismatch in two-thirds of councils.' },
      { problem: 'A council must submit a SEND reform plan to unlock its share of a £5bn deficit write-off. It cannot evidence where demand will sit in three years, so the plan is assertion rather than analysis.',
        solution: 'Compass produces the forecast the plan needs — how many children, needing what, and where — using only published figures. No individual children’s records are touched.' }
    ],

    plumbline: [
      { problem: 'A council reports 91% of major applications decided on time and is judged compliant. Measured against the actual statutory deadline it is 19%, because more than three-quarters used an agreed extension.',
        solution: 'Plumbline always shows both numbers side by side, and shows how often extensions are being used to make the headline look better.' },
      { problem: 'The Housing Delivery Test that triggers presumption-in-favour sanctions was last measured on data ending March 2023. Councils and the department are both flying blind on the mechanism meant to deliver 1.5 million homes.',
        solution: 'Plumbline keeps a running estimate going between official measurements, so everyone can see where housing delivery is heading instead of finding out two years later.' }
    ],

    highwater: [
      { problem: 'The Environment Agency objects to 47 homes on flood risk grounds. The council approves them anyway. The Agency never learns the outcome — one of 7,011 cases where it does not know what was decided.',
        solution: 'Highwater finds the decision on the council’s own public planning website and fills the gap — giving a true national figure instead of the partial sample the Agency relies on now.' },
      { problem: 'A journalist asks how many homes were built in flood zones against expert advice. Nobody can answer, because the objections file carries no address, postcode or coordinate.',
        solution: 'Highwater works out where each objection was, puts it on the flood map, and answers the question. Right now an insurance company supplies that answer to Parliament, using data it had to buy.' }
    ],

    catchment: [
      { problem: 'A council with falling rolls closes a primary school. Two miles away another is over capacity and turning children away. Both facts are true, and neither is visible in council-level statistics.',
        solution: 'Catchment publishes the missing boundaries for all 3,651 areas, so empty seats and overcrowding show up side by side inside the same council.' },
      { problem: 'Basic Need capital is allocated at planning area and year group with no offsetting between areas — so £1.096bn is distributed on a geography that is published nowhere and cannot be mapped.',
        solution: 'Catchment rebuilds those boundaries from a list the department already publishes, and gives them away free.' }
    ],

    junction: [
      { problem: 'A developer asks where they can connect 5MW within two years. Two network operators both report "available capacity" — computed on incompatible bases, because the specification delegates the calculation to each of them.',
        solution: 'Junction converts everyone’s figures to one clear definition, and publishes each operator’s own method next to it — so the numbers can finally be compared.' },
      { problem: 'The same project appears in both the transmission and distribution registers under different identifiers, with no shared key. Counting either register alone is wrong; counting both double-counts.',
        solution: 'Junction matches the two records to the same project and says how confident it is, rather than quietly guessing.' }
    ],

    ledger: [
      { problem: 'A community was promised a school alongside a 400-home development. Six years on there is no school, and nobody can show whether the money was collected, spent, or is still sitting.',
        solution: 'Ledger ties the money to the site it was promised for, and shows whether it was ever collected and whether it was ever spent.' },
      { problem: 'A council holds around £19m of unspent developer contributions and is asked publicly why. It cannot produce a spatial account of what was promised, for what, and where.',
        solution: 'Ledger puts every promise on a map — by council, by ward, by site, by what it was for. £1.49bn becomes visible for the first time.' }
    ],

    bellwether: [
      { problem: 'A care operator running more than two-thirds of one borough’s care home beds gets into difficulty. The council finds out when it reaches the news.',
        solution: 'Bellwether tracks that dependency all the time. The regulator’s own public list already names the company behind 93.9% of care home beds — nobody adds it up.' },
      { problem: 'A children’s home group appears in the register under three slightly different owner names, so its true size is invisible — and statute now requires geographical concentration to be assessed.',
        solution: 'Bellwether recognises the three names as one company. The same fix takes the biggest special school group from an apparent 30 schools to its real 51.' }
    ],

    sightline: [
      { problem: 'Active Travel England advised on planning applications covering 521,000 homes in a single year and published none of it. Government is now cutting consultee involvement by around 40%, with no data on what that advice achieved.',
        solution: 'Sightline records what was advised, what was decided and what got built — so the change can be judged on evidence rather than assumption.' },
      { problem: 'A council overrides expert advice on a development. Residents want to know whether that is unusual. No published source can tell them.',
        solution: 'Sightline publishes how often each council overrules expert advice, with the context — including that the rate has actually been flat for nine years, even though the raw numbers rose.' }
    ],

    lastmile: [
      { problem: 'A family buys a new-build and discovers there is no gigabit connection and none planned. Building regulations have required every new home to be built connectable since 2022, and nobody checks.',
        solution: 'Lastmile matches new homes to house-by-house broadband records, producing the compliance picture that has never existed for that rule.' },
      { problem: 'Public subsidy is targeted at premises that new development has already made commercially viable, because the intervention list and the development pipeline are never compared.',
        solution: 'Lastmile shows the overlap, so public money goes where companies genuinely will not build on their own.' }
    ],

    bulwark: [
      { problem: 'A flood defence fails. The council needs to know who was responsible for maintaining it. The national record says "Unknown" — as it does for 73.7% of 141,629 assets.',
        solution: 'Bulwark works out which piece of land each defence sits on, then who owns that land — and separates genuinely unowned defences from ones where nobody simply wrote it down.' },
      { problem: 'Maintenance is prioritised using a national condition figure quoted as though it covered the estate. It is computed on the quarter of assets that have a condition grade at all.',
        solution: 'Bulwark states how much of the country each figure actually covers, and flags defences whose next inspection date has already gone past.' }
    ],

    watchman: [
      { problem: 'A supplier enters administration on a Friday afternoon. Which departments, councils and services depend on it? Nobody can say before Monday, and possibly not for weeks.',
        solution: 'Watchman reads the notice. Where it carries a company number — every liquidator appointment does — the public bodies relying on that company are listed immediately, with no guessing about which company it is. Where the number is missing, the registered address in the notice still places it.' },
      { problem: 'A small supplier files accounts late two years running and takes on new charges over its assets. Both are published signals of difficulty. Nobody is watching, because the standard financial models need profit data small companies never file.',
        solution: 'Watchman treats those as facts that have happened rather than a prediction, and warns the buyers who depend on that supplier.' }
    ],

    baseline: [
      { problem: 'Spills fell 35% in a year the Environment Agency itself describes as drier than average. A regulator being stood up now must decide whether £22.1bn of investment is working, and has no weather-adjusted figure to judge it by.',
        solution: 'Baseline compares spills against how much rain actually fell nearby, using 1,044 free rain gauges — separating what the money achieved from what the weather did.' },
      { problem: 'An overflow’s recorded spill count halves — because its monitor was offline for four months. The improvement is an artefact, and the published figure does not say so.',
        solution: 'Baseline shows how long each monitor was actually working next to every spill count, so an unwatched overflow is never mistaken for a quiet one.' }
    ]

  }
};
