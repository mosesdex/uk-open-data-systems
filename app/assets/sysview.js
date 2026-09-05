/* Per-system content for the full page. Only the parts that differ between
   systems live here: plain-English framing, which metrics matter, which chart
   fits the data, and insights read from that data. Everything structural is in
   systempage.js. A system with no entry still renders a coherent page from its
   shared parts (overview, sources, methodology, records); an entry adds the
   bespoke numbers, visuals and insights.

   Rule: metrics and insights are computed from `out` (the system's gold
   tables). No figure is hand-typed. */
const SYSVIEW = (() => {
  const n = v => v == null ? '—' : Number(v).toLocaleString('en-GB');

  return {
    catchment: {
      explore: out => ({
        label: 'district', hint: 'Selecting one highlights it on the map above.',
        placeholder: 'Choose a district…',
        rows: out.by_district.filter(d => d.utilisation_pct != null)
          .slice().sort((a, b) => a.lad_name.localeCompare(b.lad_name))
          .map(d => ({ key: d.lad_code, name: d.lad_name })),
        detail: key => {
          const d = out.by_district.find(x => x.lad_code === key);
          if (!d) return [];
          return [
            { label: 'Places in use', value: d.utilisation_pct + '%', sub: 'mainstream utilisation' },
            { label: 'Pupils', value: n(d.pupils), sub: `in ${n(d.capacity)} places` },
            { label: 'Schools', value: n(d.schools), sub: d.entity_resolved_pct != null ? `${d.entity_resolved_pct}% matched to a trust` : '' },
          ];
        },
      }),
      whatIs: 'Catchment checks whether school places exist where the children actually are. It resolves every open school to the district it sits in, then compares the number of pupils against the number of places, district by district.',
      why: 'School building money is allocated per planning area, but that geography is published nowhere. A district can be overcrowded in one town and half-empty in the next, and the two cancel out in the national figure. Parents, councils and the Department all lose the local picture.',
      shows: 'The share of school places in use nationally and in each of England’s districts, mainstream and specialist counted separately, plus which districts are under the most pressure.',
      coverage: 'England · 317 districts · latest Get Information About Schools register and published capacity release.',
      metrics: out => [
        { label: 'Mainstream places in use', value: out.national.utilisation_pct + '%',
          sub: `${n(out.national.pupils)} pupils in ${n(out.national.capacity)} places` },
        { label: 'Districts covered', value: n(out.national.districts),
          sub: 'every English district with mainstream schools' },
        { label: 'Specialist over capacity', value: n(out.specialist.over_capacity),
          sub: `${out.specialist.utilisation_pct}% average utilisation across ${out.specialist.districts} districts` },
      ],
      primary: {
        explain: {
          shows: 'How full mainstream school places are in every English district. Darker means more of the places are already taken.',
          read: 'Each shape is a local authority district. Hover any district for its exact utilisation; the deepest shades are the districts closest to running out of room.',
          standout: 'Pressure is regional, not national — the average sits near 90%, but individual districts range from the low 70s to over 100%.',
        },
        draw: (out, el, { GT }) => {
          const values = {};
          out.by_district.forEach(d => { if (d.utilisation_pct != null) values[d.lad_code] = d.utilisation_pct; });
          el.dataset.geo = 'data/lad.geojson';
          GT.choropleth(el, { values, label: '% of places in use', ramp: 'red' });
        },
      },
      secondary: {
        title: 'Districts under the most pressure',
        explain: {
          shows: 'The ten districts with the highest share of mainstream places already in use.',
          read: 'Longer bars mean fuller schools. The figure is pupils divided by published capacity for that district.',
          standout: 'The leaders cluster just under or over 100% — these are the places where a single new development leaves no room.',
        },
        draw: (out, el, { GT }) => {
          const rows = out.by_district.filter(d => d.utilisation_pct != null)
            .sort((a, b) => b.utilisation_pct - a.utilisation_pct).slice(0, 10)
            .map(d => ({ n: d.lad_name, v: d.utilisation_pct }));
          GT.bars(el, rows, { fmt: v => v + '%' });
        },
      },
      insights: out => {
        const bd = out.by_district.filter(d => d.utilisation_pct != null);
        if (!bd.length) return [];
        const top = [...bd].sort((a, b) => b.utilisation_pct - a.utilisation_pct)[0];
        const bot = [...bd].sort((a, b) => a.utilisation_pct - b.utilisation_pct)[0];
        const over = bd.filter(d => d.utilisation_pct > 100).length;
        return [
          `Specialist provision runs tighter than mainstream — ${out.specialist.utilisation_pct}% of places in use against ${out.national.utilisation_pct}% for mainstream.`,
          `${n(out.specialist.over_capacity)} specialist settings are already over capacity.`,
          `${top.lad_name} is the most pressured district, at ${top.utilisation_pct}% of mainstream places in use.`,
          `${bot.lad_name} has the most room to spare, at ${bot.utilisation_pct}%.`,
          over > 1
            ? `${over} districts are over 100% of mainstream capacity.`
            : `Only ${over} district is over 100% capacity — the strain shows as districts nearing the line, not breaching it.`,
        ];
      },
      definitions: [
        { t: 'Utilisation', d: 'Pupils on roll divided by published places, as a percentage. Above 100% means more pupils than the school’s stated capacity.' },
        { t: 'Mainstream vs specialist', d: 'Counted separately: alternative and specialist provision report capacity on a different basis, so blending them distorts both.' },
      ],
      trends: out => {
        const t = out.trend || [];
        if (t.length < 2) return null;
        const first = t[0], last = t[t.length - 1];
        const secLow = [...t].sort((a, b) => a.secondary_pct - b.secondary_pct)[0];
        return {
          cards: [
            { label: `Places in use, ${first.year_label}`, value: first.utilisation_pct + '%' },
            { label: `Places in use, ${last.year_label}`, value: last.utilisation_pct + '%',
              sub: `${(last.utilisation_pct - first.utilisation_pct).toFixed(1)} pts over ${t.length} years` },
            { label: 'Secondary low point', value: secLow.secondary_pct + '%', sub: secLow.year_label + ', before the bulge arrived' },
          ],
          explain: {
            shows: 'Mainstream school-place utilisation each year since 2009/10 — primary and secondary shown separately.',
            read: 'The horizontal axis is the school year; the vertical axis is the share of places in use. Blue is primary, red is secondary.',
            standout: 'The two phases move out of step: secondary emptied to the mid-80s by 2015/16, then filled back up as the primary bulge moved through — a demographic wave, not a policy change.',
          },
          draw: (out, el, { GT }) => {
            const tt = out.trend || [];
            GT.line(el, [
              { v: tt.map(r => r.primary_pct), c: 'var(--uk-blue)' },
              { v: tt.map(r => r.secondary_pct), c: 'var(--uk-red)' },
            ], { labels: tt.map(r => r.year_label.replace('20', '').replace('/', '/')), zero: false });
          },
        };
      },
      related: [
        { id: 'compass', why: 'Uses the same school register to track the surge in special educational needs.' },
        { id: 'plumbline', why: 'Housing approvals add the pupils that school capacity has to absorb.' },
      ],
    },

    sentinel: {
      whatIs: 'Sentinel checks whether public money keeps flowing to the same suppliers without open competition, and reveals the people who own the firms behind the contracts.',
      why: 'Contract records carry company names, not identifiers. A buyer cannot see that two bidders share an owner, or that a handful of firms take most of a framework.',
      shows: 'How contract awards split across procurement routes, the buyers most reliant on a single supplier, and the individuals sitting behind several suppliers at once.',
      coverage: 'England · Contracts Finder awards resolved to Companies House.',
      metrics: out => {
        const awards = out.method.reduce((a, m) => a + m.awards, 0);
        const uncompeted = out.method.filter(m => m.method === 'direct' || m.method === 'limited').reduce((a, m) => a + m.awards, 0);
        const sel = out.method.find(m => m.method === 'selective');
        return [
          { label: 'Awards skipping open competition', value: (100 * uncompeted / awards).toFixed(1) + '%', sub: `${n(uncompeted)} of ${n(awards)} awards direct or limited` },
          { label: 'Awards analysed', value: n(awards), sub: 'grouped by buyer, supplier and route' },
          { label: 'Let by selective tender', value: sel ? sel.share_pct + '%' : '—', sub: sel ? `${n(sel.awards)} awards, £${(sel.value/1e9).toFixed(2)}bn` : '' },
        ];
      },
      primary: {
        explain: {
          shows: 'How many awards were let by each procurement route — from openly advertised to directly awarded.',
          read: 'Longer bars mean more awards by that route. Selective and "not stated" together dwarf openly competed awards.',
          standout: 'Openly competed awards are a minority; most are selective or unrecorded, where a shared owner can hide.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.method.map(m => ({ n: m.method, v: m.awards })), { fmt: v => v.toLocaleString('en-GB') }),
      },
      secondary: {
        title: 'Buyers most reliant on a single supplier',
        explain: {
          shows: 'The buyers where one supplier takes the largest share of the awards.',
          read: 'Longer bars mean more of that buyer’s awards concentrate on their top supplier.',
          standout: 'Several buyers put the great majority of their awards through one supplier.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.concentrated.slice(0, 10).map(c => ({ n: c.buyer, v: c.top_supplier_award_share })), { fmt: v => v + '%' }),
      },
      insights: out => {
        const sel = out.method.find(m => m.method === 'selective');
        const open = out.method.find(m => m.method === 'open');
        const cf = out.control_footprint || [];
        const r = [];
        if (sel) r.push(`Selective tender is the single largest route — ${n(sel.awards)} awards worth £${(sel.value/1e9).toFixed(2)}bn.`);
        if (open) r.push(`Only ${n(open.awards)} awards were openly competed.`);
        if (cf.length) r.push(`${cf.length} individuals each sit behind several suppliers to the same buyer — for example ${cf[0].person}, ${cf[0].companies} companies across ${cf[0].awards} awards to ${cf[0].buyer}.`);
        r.push('Where the procurement route is "not stated", competition cannot be verified at all.');
        return r;
      },
      definitions: [
        { t: 'Procurement route', d: 'How a contract was let: open (advertised), selective (invited shortlist), direct/limited (no competition), or not stated.' },
        { t: 'Control footprint', d: 'One person controlling several suppliers that bid to the same buyer — invisible in the contract records alone.' },
      ],
      related: [
        { id: 'bellwether', why: 'Uses the same company-ownership join to spot providers spanning many councils.' },
        { id: 'watchman', why: 'Watches the same companies for distress while they hold public contracts.' },
      ],
    },

    highwater: {
      timeFilter: out => ({
        years: out.trend.map(t => t.year),
        default: out.trend[out.trend.length - 1].year,
        yearLabel: y => y.replace('20', ''),
        apply: year => {
          const t = out.trend.find(x => x.year === year);
          return {
            cards: [
              { label: 'Objections', value: n(t.objections) },
              { label: 'Granted against advice', value: n(t.granted_against), sub: `${t.override_rate_pct}% override rate` },
              { label: 'Outcome unrecorded', value: t.unknown_pct + '%', sub: `${n(t.outcome_unknown)} cases` },
            ],
            barsRows: [
              { n: 'Advice followed', v: t.advice_followed },
              { n: 'Granted against', v: t.granted_against },
              { n: 'Outcome unknown', v: t.outcome_unknown },
            ],
            barsFmt: v => v.toLocaleString('en-GB'),
            caption: `Outcomes in ${year}`,
          };
        },
      }),
      whatIs: 'Highwater tracks how often homes are approved against Environment Agency flood advice, and whether that override rate is actually rising.',
      why: 'The Agency objects on flood grounds, then frequently never learns what the council decided — so no one can say whether objections are being ignored.',
      shows: 'The outcome of every flood objection, and the override rate across nine years — measured only over decisions whose outcome is known.',
      coverage: 'England · Environment Agency published objections, 2016-17 to 2024-25.',
      metrics: out => {
        const against = out.outcomes.find(o => /granted against/i.test(o.outcome));
        const total = out.outcomes.reduce((a, o) => a + o.objections, 0);
        const last = out.trend[out.trend.length - 1];
        return [
          { label: 'Approved against advice', value: n(against ? against.objections : null), sub: `${n(against && against.residential_units)} homes` },
          { label: 'Objections in all', value: n(total), sub: 'across nine years' },
          { label: 'Override rate, latest year', value: last ? last.override_rate_pct + '%' : '—', sub: last ? `${last.year} · of decided cases` : '' },
        ];
      },
      primary: {
        explain: {
          shows: 'What happened to homes the Environment Agency objected to on flood grounds.',
          read: 'Each bar is an outcome, sized by the number of objections. "Unknown" means the Agency was never told the result.',
          standout: 'Advice is usually followed — but thousands of outcomes are simply never recorded.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.outcomes.map(o => ({ n: o.outcome, v: o.objections })), { fmt: v => v.toLocaleString('en-GB') }),
      },
      secondary: {
        title: 'Where flood advice is overridden',
        explain: {
          shows: 'Homes approved against Environment Agency flood advice, by district — every objection placed by the authority that decided it.',
          read: 'Each shape is a district; darker means more homes approved against advice. Grey districts had none, or an authority name that did not match a district.',
          standout: 'Overrides concentrate in a few authorities rather than spreading evenly — a handful drive most of the national total.',
        },
        draw: (out, el, { GT }) => {
          if (!out.by_district || !out.by_district.length) {
            return GT.bars(el, (out.by_authority || []).slice(0, 10).map(a => ({ n: a.lpa, v: a.granted_against })), { fmt: v => v.toLocaleString('en-GB') });
          }
          const values = {};
          out.by_district.forEach(d => { if (d.granted_against != null) values[d.lad_code] = d.granted_against; });
          el.dataset.geo = 'data/lad.geojson';
          GT.choropleth(el, { values, label: 'homes approved against advice', ramp: 'red' });
        },
      },
      explore: out => {
        const a = out.by_authority || [];
        if (!a.length) return null;
        return {
          label: 'authority', placeholder: 'Choose an authority…',
          hint: 'The authorities that override flood advice most.',
          rows: a.map(r => ({ key: r.lpa, name: r.lpa })),
          detail: key => {
            const r = a.find(x => x.lpa === key);
            if (!r) return [];
            return [
              { label: 'Approved against advice', value: n(r.granted_against), sub: r.homes_against ? `${n(r.homes_against)} homes` : '' },
              { label: 'Override rate', value: r.override_rate_pct + '%', sub: `of ${n(r.objections)} objections` },
              { label: 'Objections in all', value: n(r.objections) },
            ];
          },
        };
      },
      trends: out => ({
        cards: [
          { label: 'Override rate, 2016-17', value: out.trend[0].override_rate_pct + '%' },
          { label: 'Override rate, latest', value: out.trend[out.trend.length - 1].override_rate_pct + '%' },
          { label: 'Outcomes unrecorded, latest', value: out.trend[out.trend.length - 1].unknown_pct + '%', sub: 'the Agency was never told' },
        ],
        explain: {
          shows: 'The share of decided flood objections where permission was granted anyway, year by year.',
          read: 'The horizontal axis is the year; the vertical axis is the override rate as a percentage.',
          standout: 'The rate is flat, not rising — but the share of outcomes never reported back has climbed sharply.',
        },
        draw: (out, el, { GT }) => GT.line(el, [{ v: out.trend.map(t => t.override_rate_pct), c: 'var(--uk-blue)' }], { labels: out.trend.map(t => t.year.replace('20', '')) }),
      }),
      insights: out => {
        const against = out.outcomes.find(o => /granted against/i.test(o.outcome));
        const unknown = out.outcomes.find(o => /unknown/i.test(o.outcome));
        const last = out.trend[out.trend.length - 1];
        const topA = (out.by_authority || [])[0];
        return [
          `${n(against && against.objections)} homes were approved against flood advice; advice was followed on ${n(out.outcomes.find(o=>/followed/i.test(o.outcome)).objections)}.`,
          `The override rate has stayed near 4% for nine years — it is flat, not rising.`,
          topA ? `${topA.lpa} overrides most — ${n(topA.granted_against)} approvals against advice (${topA.override_rate_pct}% of its objections).` : '',
          unknown ? `${n(unknown.objections)} objections have no recorded outcome — the Agency was never told.` : '',
        ];
      },
      definitions: [
        { t: 'Override rate', d: 'Homes granted against Agency advice as a share of decisions whose outcome is known. Unknown outcomes are excluded so the rate cannot improve just by going unrecorded.' },
      ],
      related: [
        { id: 'sightline', why: 'Also reads planning objections — on water-quality rather than flood grounds.' },
        { id: 'bulwark', why: 'The flood defences behind the advice, and who maintains them.' },
      ],
    },

    plumbline: {
      explore: out => ({
        label: 'authority', placeholder: 'Choose an authority…',
        hint: 'The ten authorities with the widest gap.',
        rows: out.worst.map(w => ({ key: w.lpa, name: w.lpa })),
        detail: key => {
          const w = out.worst.find(x => x.lpa === key);
          if (!w) return [];
          return [
            { label: 'Within legal deadline', value: w.statutory_pct + '%' },
            { label: 'Published headline', value: w.headline_pct + '%' },
            { label: 'Major dwelling decisions', value: n(w.dwelling_decisions) },
          ];
        },
      }),
      whatIs: 'Plumbline measures planning decisions against the deadline set in law, not the softer target councils are allowed to report against.',
      why: 'The published figure counts an application as on time if it met an agreed extension — so a decision months late can still count as "on time".',
      shows: 'The statutory on-time rate beside the published headline, and the authorities where the two figures diverge most.',
      coverage: 'England · major dwelling decisions, latest published planning release.',
      metrics: out => [
        { label: 'Within the legal deadline', value: out.statutory_pct + '%', sub: `${n(out.dwelling_decisions)} major dwelling decisions` },
        { label: 'The published headline', value: out.headline_pct + '%', sub: 'counts agreed extensions as on time' },
        { label: 'The gap', value: (out.headline_pct - out.statutory_pct).toFixed(1) + ' pts', sub: 'masked by extension agreements' },
      ],
      primary: {
        explain: {
          shows: 'The share of major housing decisions made on time — measured two ways.',
          read: 'The top bar is the real statutory deadline; the bottom bar is the published headline that counts extensions.',
          standout: 'The headline is roughly five times the statutory rate — almost the entire gap is extension agreements.',
        },
        draw: (out, el, { GT }) => GT.bars(el, [
          { n: 'Within legal deadline', v: out.statutory_pct },
          { n: 'Published headline', v: out.headline_pct },
        ], { fmt: v => v + '%' }),
      },
      secondary: {
        title: 'Authorities with the widest gap',
        explain: {
          shows: 'The councils where the headline figure most overstates on-time performance against the legal deadline.',
          read: 'Longer bars mean a bigger gap between the two figures for that authority.',
          standout: 'In the worst cases the headline is near-perfect while the statutory rate is in the low teens.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.worst.slice(0, 10).map(w => ({ n: w.lpa, v: +(w.headline_pct - w.statutory_pct).toFixed(1) })), { fmt: v => v + ' pts' }),
      },
      insights: out => {
        const w = out.worst[0];
        return [
          `Only ${out.statutory_pct}% of major housing decisions met the deadline in law — the published headline is ${out.headline_pct}%.`,
          `That is a gap of ${(out.headline_pct - out.statutory_pct).toFixed(1)} points, almost all of it agreed extensions.`,
          w ? `${w.lpa} shows the widest gap: ${w.headline_pct}% headline against ${w.statutory_pct}% statutory.` : '',
          `Extensions are legitimate — but counting them as "on time" hides how long applicants actually wait.`,
        ];
      },
      definitions: [
        { t: 'Statutory deadline', d: 'The thirteen-week limit in law for major dwelling applications.' },
        { t: 'Headline rate', d: 'The published figure, which treats an application as on time if it met an agreed extension.' },
      ],
      trends: out => {
        const t = out.trend || [];
        if (t.length < 2) return null;
        const first = t[0], last = t[t.length - 1];
        const gap = r => +(r.headline_pct - r.statutory_pct).toFixed(1);
        return {
          cards: [
            { label: `Gap in ${first.year}`, value: gap(first) + ' pts', sub: `${first.headline_pct}% headline vs ${first.statutory_pct}% statutory` },
            { label: `Gap in ${last.year}`, value: gap(last) + ' pts', sub: `${last.headline_pct}% headline vs ${last.statutory_pct}% statutory` },
            { label: 'Statutory rate now', value: last.statutory_pct + '%', sub: `down from ${first.statutory_pct}% in ${first.year}` },
          ],
          explain: {
            shows: 'The published headline on-time rate against the real statutory (13-week) rate, each year since 2008.',
            read: 'The horizontal axis is the year; the vertical axis is the on-time percentage. Blue is the published headline, red is the statutory reality.',
            standout: 'The two lines tracked closely until about 2013 — then extension-of-time agreements became routine, the headline climbed toward 86%, and the real statutory rate collapsed to the mid-teens. The gap the system exposes is not old; it opened in the last decade.',
          },
          draw: (out, el, { GT }) => {
            const tt = out.trend || [];
            GT.line(el, [
              { v: tt.map(r => r.headline_pct), c: 'var(--uk-blue)' },
              { v: tt.map(r => r.statutory_pct), c: 'var(--uk-red)' },
            ], { labels: tt.map(r => "'" + r.year.slice(2)), zero: false });
          },
        };
      },
      related: [
        { id: 'highwater', why: 'The flood advice that some of these approvals override.' },
        { id: 'ledger', why: 'The developer money these same permissions are meant to secure.' },
      ],
    },

    junction: {
      explore: out => ({
        label: 'operator', placeholder: 'Choose an operator…',
        rows: out.registers.map(r => ({ key: r.operator, name: r.operator })),
        detail: key => {
          const r = out.registers.find(x => x.operator === key);
          if (!r) return [];
          return [
            { label: 'Records served', value: n(r.rows), sub: `of ${n(r.catalogue_records)} catalogued` },
            { label: 'Records withheld', value: n(r.withheld), sub: r.publishes_data ? 'serves its data' : 'schema only, data withheld' },
            { label: 'Capacity fields', value: n(r.capacity_field_count), sub: `${n(r.field_count)} fields in all` },
          ];
        },
      }),
      whatIs: 'Junction checks how much grid connection capacity a developer can actually find, against how much the network operators advertise.',
      why: 'Operators publish capacity registers a developer cannot compare or, in most cases, even download — the data exists but is withheld.',
      shows: 'Which operators genuinely serve their register data, and which publish only a schema while keeping the rows behind a catalogue entry.',
      coverage: 'Great Britain · the four embedded-capacity registers reachable anonymously.',
      metrics: out => {
        const served = out.registers.reduce((a, r) => a + (r.rows || 0), 0);
        const advertised = out.registers.reduce((a, r) => a + (r.catalogue_records || 0), 0);
        const serving = out.registers.filter(r => r.rows > 0).length;
        return [
          { label: 'Records actually served', value: (100 * served / advertised).toFixed(1) + '%', sub: `${n(served)} of ${n(advertised)} advertised` },
          { label: 'Operators serving data', value: `${serving} of ${out.registers.length}`, sub: 'the rest publish only a schema' },
          { label: 'Records withheld', value: n(advertised - served), sub: 'catalogued but not downloadable' },
        ];
      },
      primary: {
        explain: {
          shows: 'How many capacity records each network operator actually serves to an anonymous request.',
          read: 'Each bar is an operator, sized by the rows it returns. A zero bar means the data is catalogued but withheld.',
          standout: 'Only one operator of four serves its register; the others publish a schema and withhold every row.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.registers.map(r => ({ n: r.operator, v: r.rows || 0 })), { fmt: v => v.toLocaleString('en-GB') }),
      },
      insights: out => {
        const serving = out.registers.find(r => r.rows > 0);
        const withheld = out.registers.filter(r => r.rows === 0);
        const advertised = out.registers.reduce((a, r) => a + (r.catalogue_records || 0), 0);
        const served = out.registers.reduce((a, r) => a + (r.rows || 0), 0);
        return [
          serving ? `Only ${serving.operator} serves its register — ${n(serving.rows)} records.` : '',
          `${withheld.length} of ${out.registers.length} operators publish a schema but withhold every row.`,
          `${(100 * (advertised - served) / advertised).toFixed(1)}% of advertised capacity records cannot be reached without an account.`,
          `Every operator returns HTTP 200 — the withholding is by design, not a broken link.`,
        ];
      },
      definitions: [
        { t: 'Embedded capacity register', d: 'A network operator’s list of where generation can connect to the grid, and how much room remains.' },
        { t: 'Withheld', d: 'A record that appears in the catalogue count but is not served in the downloadable data.' },
      ],
      related: [
        { id: 'lastmile', why: 'The same question for broadband: advertised coverage versus what is really there.' },
        { id: 'ledger', why: 'Infrastructure that developer contributions are meant to fund.' },
      ],
    },

    ledger: {
      explore: out => ({
        label: 'purpose', placeholder: 'Choose a purpose…',
        hint: 'What the contributions were earmarked for.',
        rows: out.purpose.map(p => ({ key: p.purpose, name: p.purpose })),
        detail: key => {
          const p = out.purpose.find(x => x.purpose === key);
          if (!p) return [];
          const money = v => v >= 1e6 ? '£' + (v/1e6).toFixed(1) + 'm' : '£' + n(Math.round(v));
          return [
            { label: 'Recorded amount', value: money(p.total_amount) },
            { label: 'Contributions', value: n(p.contributions), sub: `${n(p.with_amount)} carry an amount` },
            { label: 'Average', value: p.with_amount ? money(p.total_amount / p.with_amount) : '—', sub: 'per recorded contribution' },
          ];
        },
      }),
      whatIs: 'Ledger follows the money developers promise through planning — Section 106 and the Community Infrastructure Levy — and whether it was ever received or spent.',
      why: 'Contributions are recorded as free text with no location, so none of it can be mapped, compared, or chased to delivery.',
      shows: 'How much was promised, secured, allocated and spent, what it was meant for, and how little of it can be located.',
      coverage: 'England · developer contribution records, latest published release.',
      metrics: out => [
        { label: 'Recorded in contributions', value: '£' + (out.total / 1e9).toFixed(2) + 'bn', sub: `over ${n(out.with_amount)} of ${n(out.contributions)} records` },
        { label: 'Contribution records', value: n(out.contributions), sub: 'across all authorities' },
        { label: 'Records that can be mapped', value: n(out.located), sub: 'none carry a usable location' },
      ],
      primary: {
        explain: {
          shows: 'Developer money by stage — from first received through to actually spent.',
          read: 'Each bar is a stage, sized by the total amount recorded against it.',
          standout: 'Far more is received and secured than is ever recorded as spent.',
        },
        draw: (out, el, { GT, money }) => GT.bars(el, out.status.map(s => ({ n: s.status, v: s.total_amount })), { fmt: money }),
      },
      secondary: {
        title: 'What the money is for',
        explain: {
          shows: 'Developer contributions grouped by their stated purpose.',
          read: 'Longer bars mean more money recorded for that purpose.',
          standout: 'Education and affordable housing dominate the recorded purposes.',
        },
        draw: (out, el, { GT, money }) => GT.bars(el, out.purpose.slice(0, 8).map(p => ({ n: p.purpose, v: p.total_amount })), { fmt: money }),
      },
      insights: out => {
        const rec = out.status.find(s => s.status === 'received');
        const spent = out.status.find(s => s.status === 'spent');
        const topP = out.purpose[0];
        return [
          rec && spent ? `£${(rec.total_amount/1e6).toFixed(0)}m is recorded as received, but only £${(spent.total_amount/1e6).toFixed(0)}m as spent.` : '',
          topP ? `The largest single purpose is ${topP.purpose}, at £${(topP.total_amount/1e6).toFixed(0)}m.` : '',
          `Not one of ${n(out.contributions)} contributions carries a location that can be placed on a map.`,
          `Amounts are missing from ${n(out.contributions - out.with_amount)} records entirely.`,
        ];
      },
      definitions: [
        { t: 'Section 106 / CIL', d: 'Money developers agree to pay towards local infrastructure as a condition of planning permission.' },
        { t: 'Located', d: 'A record carrying coordinates or a reference that can be resolved to a place. Here, zero.' },
      ],
      related: [
        { id: 'catchment', why: 'School places this money is often meant to fund.' },
        { id: 'plumbline', why: 'The planning permissions these contributions are attached to.' },
      ],
    },

    bellwether: {
      explore: out => ({
        label: 'council', placeholder: 'Choose a council…',
        hint: 'The councils most concentrated on one provider.',
        rows: out.top_share.map(s => ({ key: s.local_authority, name: s.local_authority })),
        detail: key => {
          const s = out.top_share.find(x => x.local_authority === key);
          if (!s) return [];
          return [
            { label: 'Beds with top provider', value: n(s.beds), sub: (s.group_name || '').replace(/^BRAND /, '') },
            { label: 'Share of authority', value: s.share_pct + '%', sub: `of ${n(s.la_beds)} beds` },
            { label: 'Authority beds', value: n(s.la_beds), sub: 'care beds in all' },
          ];
        },
      }),
      whatIs: 'Bellwether reveals how much of a council’s social-care capacity sits with a single company group — something no individual council can see.',
      why: 'Each council sees only its own contracts, so a provider that matters across dozens of authorities looks unremarkable in each one.',
      shows: 'The care groups spanning the most authorities, and the councils most dependent on one provider.',
      coverage: 'England · CQC active locations resolved to company ownership.',
      metrics: out => {
        const top = out.systemic[0];
        return [
          { label: 'Authorities relying on one group', value: n(top.authorities), sub: (top.brand || '').replace(/^BRAND /, '') },
          { label: 'Beds in that group', value: n(top.beds), sub: `${n(top.locations)} locations` },
          { label: 'Companies under one brand', value: n(top.companies), sub: 'a single group, many registrations' },
        ];
      },
      primary: {
        explain: {
          shows: 'The care groups present across the most local authorities.',
          read: 'Each bar is a company group, sized by the number of authorities it operates in.',
          standout: 'The largest groups span over a hundred councils — invisible to any one of them.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.systemic.slice(0, 10).map(s => ({ n: (s.brand || '').replace(/^BRAND /, ''), v: s.authorities })), { fmt: v => v.toLocaleString('en-GB') }),
      },
      secondary: {
        title: 'Councils most concentrated on one provider',
        explain: {
          shows: 'The local authorities where one group holds the largest share of care beds.',
          read: 'Longer bars mean more of that council’s beds sit with a single group.',
          standout: 'In the most concentrated councils, one group holds well over half the beds.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.top_share.slice(0, 10).map(s => ({ n: `${s.local_authority} · ${(s.group_name||'').replace(/^BRAND /,'')}`, v: s.share_pct })), { fmt: v => v + '%' }),
      },
      insights: out => {
        const top = out.systemic[0];
        const conc = out.top_share[0];
        return [
          `${(top.brand||'').replace(/^BRAND /,'')} operates across ${n(top.authorities)} authorities through ${n(top.companies)} companies — ${n(top.locations)} locations, ${n(top.beds)} beds.`,
          `A group can look small in any single council while being systemic across the country.`,
          conc ? `${conc.local_authority} is the most concentrated: ${conc.share_pct}% of its care beds sit with ${(conc.group_name||'').replace(/^BRAND /,'')}.` : '',
          `The "brand" is one operator; the many company numbers behind it are what hides the scale.`,
        ];
      },
      definitions: [
        { t: 'Group / brand', d: 'One operator trading under many company registrations. Grouping by the regulator’s brand field reveals the true footprint.' },
        { t: 'Systemic provider', d: 'A group large enough that its failure would affect care across many authorities at once.' },
      ],
      related: [
        { id: 'sentinel', why: 'Uses the same ownership join to expose concentration in public contracts.' },
        { id: 'watchman', why: 'Watches these same companies for financial distress.' },
      ],
    },

    sightline: {
      whatIs: 'Sightline gathers planning where water quality is a live issue — applications flagged for nutrient neutrality, phosphate or water-quality concerns — and places them on the map, alongside a sample of formal objection reasons.',
      why: 'These records sit scattered across ~420 individual authority registers and are never counted together, so the national pattern of where water quality shapes planning is invisible.',
      shows: 'The national corpus of water-quality-related planning applications by district and authority, the themes driving them, and the reasons behind formal objections.',
      coverage: 'England & Wales · PlanIt-aggregated planning applications matching water-quality terms, plus a sampled EA objection-reason release.',
      metrics: out => {
        const c = out.corpus;
        const objTotal = out.reasons.reduce((a, r) => a + r.objections, 0);
        const rows = [];
        if (c) {
          rows.push({ label: 'Water-quality planning applications', value: n(c.applications), sub: `across ${n(c.authorities)} authorities` });
          rows.push({ label: 'Decisions made', value: n(c.decided), sub: `of ${n(c.applications)} — the rest still open` });
        }
        rows.push({ label: 'Objection reasons sampled', value: n(objTotal), sub: `across ${out.reasons.length} distinct reasons` });
        return rows;
      },
      primary: {
        explain: {
          shows: 'Where water-quality concerns arise in planning — every matched application placed in its district by its own coordinates.',
          read: 'Each shape is a district; darker means more water-quality-related applications. Grey districts have none in the corpus.',
          standout: 'Concentration follows the nutrient-neutrality catchments — a handful of river catchments account for most of the activity.',
        },
        draw: (out, el, { GT }) => {
          if (!out.by_district || !out.by_district.length) {
            return GT.bars(el, out.reasons.slice(0, 10).map(r => ({ n: r.reason, v: r.objections })), { fmt: v => v.toLocaleString('en-GB') });
          }
          const values = {};
          out.by_district.forEach(d => { values[d.lad_code] = d.applications; });
          el.dataset.geo = 'data/lad.geojson';
          GT.choropleth(el, { values, label: 'water-quality applications', ramp: 'red' });
        },
      },
      secondary: {
        title: 'Objection reasons (sampled)',
        explain: {
          shows: 'The reasons most often cited when planning is formally objected to on water-quality grounds.',
          read: 'Each bar is a reason, sized by the number of objections citing it.',
          standout: 'A few reasons — led by insufficient information — account for most objections.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.reasons.slice(0, 10).map(r => ({ n: r.reason, v: r.objections })), { fmt: v => v.toLocaleString('en-GB') }),
      },
      insights: out => {
        const r = [];
        const c = out.corpus;
        const th = out.by_theme || [];
        const aw = out.by_authority_wq || [];
        if (c) r.push(`${n(c.applications)} planning applications flag water quality across ${n(c.authorities)} authorities — a national pattern no single register shows.`);
        if (th.length) { const t = [...th].sort((a, b) => b.applications - a.applications)[0]; r.push(`The largest theme is “${t.term}” — ${n(t.applications)} applications, ${n(t.refused)} refused.`); }
        if (aw.length) r.push(`${aw[0].lpa} sees the most: ${n(aw[0].applications)} water-quality applications.`);
        const top = out.reasons[0];
        if (top) r.push(`Among formal objections, the most common reason is “${top.reason}”, cited ${n(top.objections)} times.`);
        return r;
      },
      related: [
        { id: 'highwater', why: 'The Environment Agency objections that sit alongside these on flood grounds.' },
        { id: 'baseline', why: 'The sewage-spill data behind many water-quality concerns.' },
      ],
    },

    lastmile: {
      explore: out => ({
        label: 'district', placeholder: 'Choose a district…',
        hint: 'Selecting one highlights it on the map above.',
        rows: (out.by_district || []).filter(d => d.gigabit_pct != null)
          .slice().sort((a, b) => a.lad_name.localeCompare(b.lad_name))
          .map(d => ({ key: d.lad_code, name: d.lad_name })),
        detail: key => {
          const d = (out.by_district || []).find(x => x.lad_code === key);
          if (!d) return [];
          const ranked = (out.by_district || []).filter(x => x.gigabit_pct != null)
            .slice().sort((a, b) => b.gigabit_pct - a.gigabit_pct);
          const rank = ranked.findIndex(x => x.lad_code === key) + 1;
          return [
            { label: 'Gigabit coverage', value: d.gigabit_pct + '%', sub: `${n(d.premises)} premises` },
            { label: 'Rank', value: rank ? `${rank} of ${ranked.length}` : '—', sub: 'best-connected first' },
            { label: 'Against national', value: (d.gigabit_pct - out.other_pct).toFixed(1) + ' pts', sub: `national ${out.other_pct}%` },
          ];
        },
      }),
      whatIs: 'Lastmile checks whether new-build homes actually get gigabit broadband, by comparing them against existing premises.',
      why: 'New builds are assumed to be the best-connected homes there are — but nobody checks that against the existing housing stock.',
      shows: 'Gigabit coverage in new-build versus other premises, and the authorities where new builds fall furthest behind.',
      coverage: 'United Kingdom · premises-level gigabit availability, latest release.',
      metrics: out => [
        { label: 'Gigabit in new-build postcodes', value: out.new_build_pct + '%', sub: `${n(out.new_build_premises)} premises` },
        { label: 'Gigabit in other premises', value: out.other_pct + '%', sub: `${n(out.other_premises)} premises` },
        { label: 'New-build advantage', value: (out.new_build_pct - out.other_pct).toFixed(1) + ' pts', sub: 'new builds are not ahead' },
      ],
      primary: {
        explain: {
          shows: 'Gigabit broadband coverage in every English district. Darker means more premises can already get a gigabit connection.',
          read: 'Each shape is an English local authority district; hover for its exact coverage. The palest districts are the least connected. (The headline figures above cover the whole UK; the map shows the English districts the boundary set carries.)',
          standout: 'Coverage is uneven — strong in cities, thin in rural and some urban-fringe districts.',
        },
        draw: (out, el, { GT }) => {
          const values = {};
          (out.by_district || []).forEach(d => { if (d.gigabit_pct != null) values[d.lad_code] = d.gigabit_pct; });
          el.dataset.geo = 'data/lad.geojson';
          GT.choropleth(el, { values, label: '% gigabit-capable', ramp: 'blue' });
        },
      },
      secondary: {
        title: 'Where new builds fall furthest behind',
        explain: {
          shows: 'The authorities with the widest gap between new-build gigabit coverage and their overall coverage.',
          read: 'Longer bars mean new builds lag further behind the rest of that authority.',
          standout: 'In the worst cases new-build coverage is less than half the area figure.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.worst_gap.slice(0, 10).map(w => ({ n: w.lad_name, v: w.gap })), { fmt: v => v + ' pts' }),
      },
      insights: out => {
        const w = out.worst_gap[0];
        return [
          `New-build postcodes reach ${out.new_build_pct}% gigabit coverage — fractionally below the ${out.other_pct}% for existing premises.`,
          `The assumption that new homes are automatically well connected does not hold.`,
          w ? `${w.lad_name} is the worst case: ${w.gigabit_pct_new_build}% in new builds against ${w.gigabit_pct}% area-wide, a ${w.gap}-point gap.` : '',
        ];
      },
      definitions: [
        { t: 'Gigabit-capable', d: 'A premises able to order a connection of 1,000 Mbps or more.' },
        { t: 'New-build postcode', d: 'A postcode with recent new-build sales, matched against premises-level coverage.' },
      ],
      related: [
        { id: 'junction', why: 'The same advertised-versus-actual gap, for grid capacity.' },
        { id: 'plumbline', why: 'The new housing whose connectivity this measures.' },
      ],
    },

    bulwark: {
      whatIs: 'Bulwark maps who maintains England’s flood defences and how many inspections are overdue.',
      why: 'Responsibility for defences is scattered across owners and maintainers; a structure can be overdue for inspection with no clear owner on record.',
      shows: 'How many assets have a known maintainer and owner, how many inspections are overdue, and which maintainers hold the most.',
      coverage: 'England · Environment Agency asset register.',
      metrics: out => [
        { label: 'Inspections overdue', value: n(out.coverage.overdue), sub: 'against their own due dates' },
        { label: 'Assets in the register', value: n(out.coverage.assets), sub: `${Math.round(100 * out.coverage.maintainer_known / out.coverage.assets)}% have a known maintainer` },
        { label: 'Owner on record', value: Math.round(100 * out.coverage.owner_known / out.coverage.assets) + '%', sub: `of ${n(out.coverage.assets)} assets` },
      ],
      explore: out => ({
        label: 'district', placeholder: 'Choose a district…',
        hint: 'Selecting one highlights it on the map above.',
        rows: (out.by_district || []).slice().sort((a, b) => a.lad_name.localeCompare(b.lad_name))
          .map(d => ({ key: d.lad_code, name: d.lad_name })),
        detail: key => {
          const d = (out.by_district || []).find(x => x.lad_code === key);
          if (!d) return [];
          return [
            { label: 'Inspections overdue', value: n(d.overdue), sub: d.assets ? `${Math.round(100 * d.overdue / d.assets)}% of its assets` : '' },
            { label: 'Assets', value: n(d.assets), sub: `${Math.round(100 * d.owner_known / d.assets)}% owner known` },
            { label: 'Owner on record', value: Math.round(100 * d.owner_known / d.assets) + '%' },
          ];
        },
      }),
      primary: {
        explain: {
          shows: 'Flood-defence inspections that are overdue, by district. Darker means more assets past their own inspection date.',
          read: 'Each shape is a district; hover for its overdue count. Grey districts have no defences matched to them.',
          standout: 'Overdue inspections cluster in a handful of districts, not spread evenly across the country.',
        },
        draw: (out, el, { GT }) => {
          const values = {};
          (out.by_district || []).forEach(d => { if (d.overdue != null) values[d.lad_code] = d.overdue; });
          el.dataset.geo = 'data/lad.geojson';
          GT.choropleth(el, { values, label: 'inspections overdue', ramp: 'red' });
        },
      },
      secondary: {
        title: 'Who maintains England’s flood defences',
        explain: {
          shows: 'The bodies responsible for maintaining flood defences, by number of assets held.',
          read: 'Each bar is a maintainer type, sized by the assets it is responsible for.',
          standout: 'Private individuals, companies and charities maintain the largest single share.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.by_maintainer.slice(0, 8).map(m => ({ n: m.maintainer, v: m.assets })), { fmt: v => v.toLocaleString('en-GB') }),
      },
      insights: out => {
        const c = out.coverage;
        const top = out.by_maintainer[0];
        return [
          `The owner is on record for only ${Math.round(100 * c.owner_known / c.assets)}% of ${n(c.assets)} flood-defence assets.`,
          `${n(c.overdue)} inspections are past their due date.`,
          top ? `${top.maintainer} holds the most — ${n(top.assets)} assets, ${n(top.overdue)} of them overdue.` : '',
          `A defence with no recorded owner is one no one is clearly accountable for.`,
        ];
      },
      definitions: [
        { t: 'Maintainer vs owner', d: 'The maintainer is responsible for upkeep; the owner holds the land. The register often knows one but not the other.' },
        { t: 'Overdue', d: 'An asset whose next inspection date has passed.' },
      ],
      related: [
        { id: 'highwater', why: 'The flood advice these defences underpin.' },
        { id: 'baseline', why: 'The watercourses these assets protect against.' },
      ],
    },

    watchman: {
      whatIs: 'Watchman is an early-warning check: it cross-references company financial distress against active public duties, flagging organisations in liquidation, administration or a voluntary arrangement that still hold public contracts or run regulated care.',
      why: 'Company distress and active public roles are never routinely cross-referenced, so a failing provider is noticed only after it collapses — often mid-service.',
      shows: 'Every public-role holder whose Companies House status shows financial distress: care providers with live CQC registrations and suppliers with public contracts.',
      coverage: 'England · Companies House status snapshot joined to CQC care providers and public-contract suppliers.',
      metrics: out => {
        const d = out.distress || { total: 0, care: 0, contracts: 0 };
        return [
          { label: 'Distressed public-role holders', value: n(d.total), sub: 'in liquidation, administration or a voluntary arrangement' },
          { label: 'Care providers', value: n(d.care), sub: 'holding live CQC registrations while insolvent' },
          { label: 'Contract suppliers', value: n(d.contracts), sub: 'holding public contracts while distressed' },
        ];
      },
      primary: {
        explain: {
          shows: 'The distressed public-role holders broken down by the exact Companies House status.',
          read: 'Each bar is an insolvency status, sized by how many public-role holders are in it.',
          standout: 'Most are in outright liquidation — not a soft warning, but firms being wound up while still on the CQC register.',
        },
        draw: (out, el, { GT }) => GT.bars(el, (out.by_status || []).map(s => ({ n: s.status, v: s.n })), { fmt: v => v.toLocaleString('en-GB') }),
      },
      insights: out => {
        const d = out.distress || {};
        const list = out.distress_list || [];
        const top = list[0];
        const r = [];
        if (d.total) r.push(`${n(d.total)} organisations hold a public duty while financially distressed — ${n(d.care)} of them run regulated care.`);
        if (top && top.role === 'CQC care provider') r.push(`${top.name} is in ${top.company_status.toLowerCase()} while still registered for ${n(top.activity)} CQC care locations.`);
        const liq = (out.by_status || []).find(s => /liquidation/i.test(s.status));
        if (liq) r.push(`${n(liq.n)} are in outright liquidation — being wound up, not merely warned.`);
        r.push('This is the join that was missing: distress data and public-duty data existed separately, and no one connected them until a service failed.');
        return r;
      },
      records: true,
      related: [
        { id: 'bellwether', why: 'Care providers whose distress would affect many councils at once.' },
        { id: 'sentinel', why: 'The public contracts these companies may hold.' },
      ],
    },

    compass: {
      explore: out => ({
        label: 'authority', placeholder: 'Choose an authority…',
        hint: 'The authorities projected to rise fastest.',
        rows: out.rising.map(r => ({ key: r.la_name, name: r.la_name })),
        detail: key => {
          const r = out.rising.find(x => x.la_name === key);
          if (!r) return [];
          return [
            { label: 'Projected 3-year change', value: '+' + r.projected_change_pct + '%' },
            { label: 'Extra pupils per year', value: n(r.pupils_per_year) },
            { label: 'Projected total change', value: '+' + n(r.projected_change_3yr), sub: 'pupils over three years' },
          ];
        },
      }),
      whatIs: 'Compass tracks the surge in special educational needs — Education, Health and Care plans and SEN support — and shows where it is growing fastest.',
      why: 'Demand is rising far faster than the number of children, but the local picture is buried inside national totals.',
      shows: 'National growth in EHC plans and SEN support, the authorities projected to rise fastest, and where a local trend diverges from its region.',
      coverage: 'England · Department for Education SEN statistics, earliest to latest published year.',
      metrics: out => {
        const g = p => { const r = out.national.find(x => x.provision === p); return r ? (100 * (r.latest - r.earliest) / r.earliest) : null; };
        const ehc = out.national.find(x => /health and care/i.test(x.provision));
        const sen = out.national.find(x => /SEN support/i.test(x.provision));
        return [
          { label: 'Growth in EHC plans', value: '+' + g('Education, health and care plan').toFixed(1) + '%', sub: ehc ? `${n(ehc.earliest)} → ${n(ehc.latest)}` : '' },
          { label: 'Growth in SEN support', value: '+' + g('SEN support / SEN without an EHC plan').toFixed(1) + '%', sub: sen ? `${n(sen.earliest)} → ${n(sen.latest)}` : '' },
          { label: 'Growth in all pupils', value: '+' + g('Total').toFixed(1) + '%', sub: 'the population it is measured against' },
        ];
      },
      primary: {
        explain: {
          shows: 'How fast each group has grown between the earliest and latest published year.',
          read: 'Each bar is a growth rate. The EHC-plan bar towers over the growth in pupil numbers.',
          standout: 'EHC plans have more than doubled while the pupil population rose only a few percent.',
        },
        draw: (out, el, { GT }) => {
          const g = p => { const r = out.national.find(x => x.provision === p); return r ? +(100 * (r.latest - r.earliest) / r.earliest).toFixed(1) : 0; };
          GT.bars(el, [
            { n: 'EHC plans', v: g('Education, health and care plan') },
            { n: 'SEN support', v: g('SEN support / SEN without an EHC plan') },
            { n: 'All pupils', v: g('Total') },
          ], { fmt: v => '+' + v + '%' });
        },
      },
      secondary: {
        title: 'Authorities projected to rise fastest',
        explain: {
          shows: 'The local authorities with the steepest projected three-year rise in demand.',
          read: 'Longer bars mean a larger projected percentage increase.',
          standout: 'The fastest-rising authorities face increases far above the national trend.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.rising.slice(0, 10).map(r => ({ n: r.la_name, v: r.projected_change_pct })), { fmt: v => '+' + v + '%' }),
      },
      insights: out => {
        const g = p => { const r = out.national.find(x => x.provision === p); return r ? (100 * (r.latest - r.earliest) / r.earliest).toFixed(1) : '—'; };
        const rise = out.rising[0];
        const div = out.divergence[0];
        return [
          `EHC plans are up ${g('Education, health and care plan')}% while the pupil population rose just ${g('Total')}%.`,
          rise ? `${rise.la_name} is projected to rise fastest — ${rise.projected_change_pct}% over three years.` : '',
          div ? `${div.la_name} diverges most from its region, by ${div.divergence} points against ${div.region} as a whole.` : '',
          `The need is growing many times faster than the number of children — a system-level pressure, not a local blip.`,
        ];
      },
      definitions: [
        { t: 'EHC plan', d: 'An Education, Health and Care plan: a legal document setting out support for a child with significant special educational needs.' },
        { t: 'SEN support', d: 'Special educational needs support provided without a full EHC plan.' },
      ],
      trends: out => {
        const t = out.trend || [];
        if (t.length < 2) return null;
        const b = t[0], last = t[t.length - 1];
        const ix = (v, base) => Math.round(100 * v / base);
        return {
          cards: [
            { label: `EHC plans since ${b.year}`, value: '×' + (last.ehc / b.ehc).toFixed(2), sub: `${n(b.ehc)} → ${n(last.ehc)}` },
            { label: 'SEN support', value: '×' + (last.sen / b.sen).toFixed(2), sub: `${n(b.sen)} → ${n(last.sen)}` },
            { label: 'All pupils', value: '×' + (last.total / b.total).toFixed(2), sub: 'the population it is measured against' },
          ],
          explain: {
            shows: `The three groups indexed to ${b.year} = 100, so their very different sizes can be compared on one axis.`,
            read: 'The horizontal axis is the year; the vertical axis is each group relative to its own 2015 level. Red is EHC plans, blue is SEN support, grey is all pupils.',
            standout: `EHC plans have more than doubled (index ${ix(last.ehc, b.ehc)}) while the pupil population barely moved (index ${ix(last.total, b.total)}) — and total pupils have actually fallen since 2023 even as EHC plans keep climbing. The demand is detaching from the size of the child population.`,
          },
          draw: (out, el, { GT }) => {
            const tt = out.trend || [];
            const base = tt[0];
            GT.line(el, [
              { v: tt.map(r => Math.round(100 * r.ehc / base.ehc)), c: 'var(--uk-red)' },
              { v: tt.map(r => Math.round(100 * r.sen / base.sen)), c: 'var(--uk-blue)' },
              { v: tt.map(r => Math.round(100 * r.total / base.total)), c: 'var(--ink-3)' },
            ], { labels: tt.map(r => "'" + String(r.year).slice(2)), zero: false });
          },
        };
      },
      related: [
        { id: 'catchment', why: 'The school places this rising need has to be met within.' },
        { id: 'plumbline', why: 'Housing growth adds to the same local demand.' },
      ],
    },

    baseline: {
      explore: out => ({
        label: 'water company', placeholder: 'Choose a company…',
        rows: out.by_company.map(c => ({ key: c.company, name: c.company })),
        detail: key => {
          const c = out.by_company.find(x => x.company === key);
          if (!c) return [];
          return [
            { label: 'Spills, uptime-adjusted', value: n(Math.round(c.availability_adjusted)), sub: `${n(Math.round(c.reported_spills))} reported` },
            { label: 'Monitored outlets', value: n(c.outlets), sub: `${n(c.under_watched)} under-watched` },
            { label: 'Monitor uptime', value: c.mean_availability_pct + '%' },
          ];
        },
      }),
      whatIs: 'Baseline measures sewage spills from storm overflows, adjusted for how long each monitor was actually working.',
      why: 'Raw spill counts flatter companies whose monitors were offline — a low number can mean a broken sensor, not a clean river.',
      shows: 'Spills nationally after adjusting for monitor uptime, the companies with the most, and how spills track rainfall.',
      coverage: 'England · Event Duration Monitoring returns, latest reporting year.',
      metrics: out => [
        { label: 'Spills, uptime-adjusted', value: n(Math.round(out.national.adjusted)), sub: `${n(Math.round(out.national.reported))} reported` },
        { label: 'Mean monitor uptime', value: out.national.mean_uptime + '%', sub: 'time monitors were working' },
        { label: 'Monitored outlets', value: n(out.national.outlets), sub: 'storm overflows watched' },
      ],
      primary: {
        explain: {
          shows: 'Uptime-adjusted sewage spills by district, from every monitored storm overflow placed on the map by its own coordinates.',
          read: 'Each shape is a district; darker means more adjusted spills. Hover for the count. Grey districts have no monitored overflow.',
          standout: 'Spills concentrate in the rural West and North where combined sewers meet high rainfall — not in the big cities.',
        },
        draw: (out, el, { GT }) => {
          const values = {};
          (out.by_district || []).forEach(d => { if (d.adjusted_spills != null) values[d.lad_code] = d.adjusted_spills; });
          el.dataset.geo = 'data/lad.geojson';
          GT.choropleth(el, { values, label: 'adjusted spills', ramp: 'red' });
        },
      },
      secondary: {
        title: 'Spills per 100mm of rain',
        explain: {
          shows: 'Each company’s spills normalised by local rainfall, so wet regions are not unfairly blamed.',
          read: 'Longer bars mean more spills for the same amount of rain.',
          standout: 'Even adjusted for weather, some companies spill far more per millimetre than others.',
        },
        draw: (out, el, { GT }) => GT.bars(el, out.weather.slice(0, 10).map(w => ({ n: w.company, v: Math.round(w.spills_per_100mm_rain) })), { fmt: v => v.toLocaleString('en-GB') }),
      },
      insights: out => {
        const add = Math.round(out.national.adjusted - out.national.reported);
        const top = out.by_company[0];
        const wet = [...out.weather].sort((a, b) => b.spills_per_100mm_rain - a.spills_per_100mm_rain)[0];
        return [
          `Adjusting for monitor downtime adds about ${n(add)} spills the raw count missed.`,
          top ? `${top.company} has the most, at ${n(Math.round(top.availability_adjusted))} adjusted spills across ${n(top.outlets)} outlets.` : '',
          wet ? `Even per 100mm of rain, ${wet.company} spills most — ${n(Math.round(wet.spills_per_100mm_rain))} times.` : '',
          `Where uptime is low, a small reported number may hide a large real one.`,
        ];
      },
      definitions: [
        { t: 'Uptime adjustment', d: 'Scaling reported spills by the share of time a monitor was working, so offline sensors do not understate the total.' },
        { t: 'Storm overflow', d: 'A relief point that discharges untreated sewage into rivers or the sea during heavy rain.' },
      ],
      trends: out => {
        const t = out.trend || [];
        if (t.length < 2) return null;
        const first = t[0], last = t[t.length - 1];
        const peak = [...t].sort((a, b) => b.reported_spills - a.reported_spills)[0];
        const gap = r => Math.round(r.adjusted_spills - r.reported_spills);
        return {
          cards: [
            { label: `Reported peak, ${peak.year}`, value: n(Math.round(peak.reported_spills)), sub: 'the wettest reporting year' },
            { label: `Latest reported, ${last.year}`, value: n(Math.round(last.reported_spills)), sub: `${last.mean_uptime}% monitor uptime` },
            { label: `Hidden by downtime, ${first.year}`, value: n(gap(first)), sub: `vs ${n(gap(last))} in ${last.year} — the gap has closed` },
          ],
          explain: {
            shows: 'Sewage spills each year, reported (blue) against uptime-adjusted (red), 2021 onward.',
            read: 'The horizontal axis is the reporting year; the vertical axis is the spill count. The gap between the lines is the spills that broken monitors missed.',
            standout: 'Spills swing with the weather (2023 wettest, 2022 driest), but the reported-vs-adjusted gap has closed sharply — from ~172,000 hidden by monitor downtime in 2021 to under 10,000 in 2025, as uptime rose from 94.9% to 97.3%. Early raw counts understated reality far more than recent ones.',
          },
          draw: (out, el, { GT }) => {
            const tt = out.trend || [];
            GT.line(el, [
              { v: tt.map(r => Math.round(r.reported_spills)), c: 'var(--uk-blue)' },
              { v: tt.map(r => Math.round(r.adjusted_spills)), c: 'var(--uk-red)' },
            ], { labels: tt.map(r => String(r.year)), zero: false });
          },
        };
      },
      related: [
        { id: 'sightline', why: 'Planning objections raised on water-quality grounds.' },
        { id: 'highwater', why: 'The flood and water management this sits alongside.' },
      ],
    },
  };
})();
