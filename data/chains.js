// How the thirteen systems compound. Consumed by build.js.
export default {
  intro: [
    'Two resolution layers are what make thirteen systems one platform rather than thirteen products. But the reason it is worth building as a platform is not the shared plumbing — it is that a single event or a single reference reaches across several systems at once.',
    'Each chain below starts with one fact arriving. Nothing in any of them requires new data; every step runs on sources that return data to an anonymous request.'
  ],

  chains: [
    {
      trigger: 'A company enters insolvency proceedings',
      spine: 'entity',
      steps: [
        ['Watchman', 'Reads the notice from the official insolvency record, which carries a structured company number — so the organisation is identified without name matching.'],
        ['Bellwether', 'Checks that company against the care registers. If it operates care homes, children’s homes or special schools, the councils depending on it are known immediately — including any where it holds a large share of local capacity.'],
        ['Sentinel', 'Checks the same company against the public procurement record. Which contracts does it hold, with which buyers, worth how much.'],
        ['Ledger', 'If it is a developer, checks what contributions it owes and whether they have been paid.']
      ],
      outcome: 'An exposure answer in minutes, for an event the public sector currently discovers by reading the news. This is the capability whose absence was the lesson of the 2018 contractor collapse.'
    },
    {
      trigger: 'A planning permission is granted',
      spine: 'place',
      steps: [
        ['Plumbline', 'Records the decision and how long it actually took — against the statutory deadline, not the extended one.'],
        ['Ledger', 'Attaches the developer contributions agreed with it, and tracks whether they are received and spent.'],
        ['Sightline', 'Checks whether a statutory consultee objected, and whether the objection was followed.'],
        ['Highwater', 'Checks whether the site sits in a flood zone, and whether the Environment Agency advised against it.'],
        ['Catchment', 'Feeds the homes into school place forecasting for the planning area it falls in.'],
        ['Lastmile', 'Checks whether the site has gigabit infrastructure, and whether the homes were built connectable.']
      ],
      outcome: 'Six systems reading one planning reference. Today each of those questions is answered separately, by different bodies, at different geographies, mostly not at all.'
    },
    {
      trigger: 'An asset has no recorded owner',
      spine: 'both',
      steps: [
        ['Bulwark', 'Holds 141,629 flood defences, 73.7% with owner recorded as unknown, all geolocated.'],
        ['Place spine', 'Resolves each asset to the land parcel it sits on.'],
        ['Entity spine', 'Resolves that parcel to an organisation, where one is registered.'],
        ['Watchman', 'Flags where that organisation is in financial distress — because a defence owned by a failing company is a different risk from one owned by a solvent one.']
      ],
      outcome: 'Closing a gap the Environment Agency reports on three-quarters of its own asset register, using only the resolution capability the platform already has.'
    },
    {
      trigger: 'A regulator changes its identifier scheme',
      spine: 'entity',
      steps: [
        ['Baseline', 'Storm overflow identifiers changed in 2024 — the published data still carries the old identifier in a separate field, and multi-year analysis breaks across the change.'],
        ['Junction', 'Grid connection registers share no identifier between transmission and distribution, so the same project appears twice with no link.'],
        ['Entity spine', 'The same resolution technique applied to physical assets rather than organisations, with match confidence published rather than asserted.'],
        ['Bellwether', 'The same problem again in care — owner names published without company numbers.']
      ],
      outcome: 'One capability, four sectors. Identity breaks are the single most common reason a national dataset cannot be analysed over time, and almost nobody fixes them.'
    }
  ],

  reuse: {
    intro: 'The compounding also runs the other way. Work done for one system lowers the cost of the next.',
    items: [
      ['The planning reference resolver', 'Built for Ledger, reused by Highwater, Sightline, Plumbline and Catchment. Five systems, one hard problem solved once.'],
      ['The corporate graph', 'Assembled for Sentinel, reused by Bellwether, Watchman and Freehold. The beneficial ownership register is a free daily download, so the marginal cost of the fourth consumer is near zero.'],
      ['Coverage reporting', 'Every system publishes what share of England it actually represents. Built once as a discipline, applied everywhere — and it is the thing that makes the outputs trustworthy to a statistician.'],
      ['Match confidence', 'No system asserts a resolution it cannot evidence. The same confidence machinery serves all thirteen, and it is what makes the work defensible when a named organisation objects.']
    ]
  }
};
