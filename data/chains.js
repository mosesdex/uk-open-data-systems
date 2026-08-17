// How the thirteen systems help each other. Consumed by build.js.
export default {
  intro: [
    'Sharing the same plumbing is not the interesting part. The interesting part is that one piece of news, or one reference number, sets off several systems at once.',
    'Each example below starts with a single fact arriving. None of them needs new data — every step uses something anyone can already download for free.'
  ],

  chains: [
    {
      trigger: 'A company goes bust',
      spine: 'entity',
      label: 'WHO',
      steps: [
        ['Watchman spots it', 'The official insolvency notice includes the company number, so there is no guessing about which company it is.'],
        ['Bellwether checks care', 'Does it run care homes, children’s homes or special schools? If so, which councils just lost capacity — and does any council depend on it heavily?'],
        ['Sentinel checks contracts', 'Which public contracts does it hold, with whom, and worth how much?'],
        ['Ledger checks building', 'If it is a housebuilder, what did it still owe councils, and had it paid?']
      ],
      outcome: 'You know the damage within minutes. Today the public sector usually finds out by reading the news — which is exactly what went wrong when a major government contractor collapsed in 2018.'
    },
    {
      trigger: 'A council approves a housing development',
      spine: 'place',
      label: 'WHERE',
      steps: [
        ['Plumbline', 'Records how long the decision really took — measured against the legal deadline, not an extended one.'],
        ['Ledger', 'Picks up what the builder agreed to pay for schools and roads, and whether that money ever arrives.'],
        ['Sightline', 'Checks whether an expert body objected, and whether the council listened.'],
        ['Highwater', 'Checks whether it is in a flood zone, and whether the Environment Agency warned against it.'],
        ['Catchment', 'Adds the new homes to the school places forecast for that neighbourhood.'],
        ['Lastmile', 'Checks whether the homes will actually have decent broadband.']
      ],
      outcome: 'Six systems, one reference number. Today those six questions are handled by different bodies, at different scales, and mostly not at all.'
    },
    {
      trigger: 'Nobody knows who owns a flood defence',
      spine: 'both',
      label: 'WHERE + WHO',
      steps: [
        ['The problem', 'England has 141,629 flood defences. The owner is recorded as “Unknown” on nearly three-quarters of them.'],
        ['The where link', 'Works out which piece of land each defence sits on.'],
        ['The who link', 'Works out who owns that land, where an owner is registered.'],
        ['Watchman', 'Flags if that owner is in financial trouble — a defence owned by a failing company is a different risk from one owned by a healthy one.']
      ],
      outcome: 'A gap the Environment Agency reports on its own records, closed using only what the platform already does for everything else.'
    },
    {
      trigger: 'A regulator changes its reference numbers',
      spine: 'entity',
      label: 'WHO',
      steps: [
        ['Sewage', 'Storm overflow reference numbers changed in 2024. The old ones sit in a separate column, so nobody can track an overflow across the change.'],
        ['Electricity', 'Grid connection projects appear in two registers with different numbers and no link, so the same project gets counted twice.'],
        ['Care', 'Care providers are listed by owner name with no company number, so one group looks like three.'],
        ['Same fix, every time', 'Match them up, and say how confident the match is rather than pretending it is certain.']
      ],
      outcome: 'One skill, four industries. Changed reference numbers are the most common reason a national dataset cannot be tracked over time — and almost nobody fixes them.'
    }
  ],

  reuse: {
    intro: 'It also works in reverse. Whatever gets built for one system makes the next one cheaper.',
    items: [
      ['Turning planning references into map points', 'Built for Ledger. Reused straight away by Highwater, Sightline, Plumbline and Catchment. Five systems, one hard problem solved once.'],
      ['Working out who owns which company', 'Built for Sentinel. Reused by Bellwether and Watchman. The ownership register is a free daily download, so the third and fourth users cost almost nothing.'],
      ['Saying how much of the country is covered', 'Every system says plainly what share of England it actually represents. Built once as a habit, applied everywhere — and it is what makes a statistician trust the numbers.'],
      ['Saying how sure we are', 'No system claims a match it cannot prove. The same machinery serves all thirteen, and it is what holds up when a named company objects.']
    ]
  }
};
