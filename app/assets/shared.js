/* Shared reference data for the three prototype interfaces. */
const SYSTEMS = [
  {id:'catchment', n:'Catchment',  s:'School place planning at the geography that matters', spine:'place',  st:'live',  dom:'Education'},
  {id:'sentinel',  n:'Sentinel',   s:'Public procurement integrity and collusion detection', spine:'entity', st:'live',  dom:'Procurement'},
  {id:'highwater', n:'Highwater',  s:'Flood risk against what actually got built',           spine:'place',  st:'live',  dom:'Environment'},
  {id:'plumbline', n:'Plumbline',  s:'Housing decisions measured against the statutory 13 weeks',  spine:'place',  st:'live',  dom:'Housing'},
  {id:'junction',  n:'Junction',   s:'Grid connection capacity on one definition',           spine:'both',   st:'beta',  dom:'Energy'},
  {id:'ledger',    n:'Ledger',     s:'Developer contributions traced to the site',           spine:'place',  st:'live',  dom:'Housing'},
  {id:'bellwether',n:'Bellwether', s:'Provider concentration in care and education',         spine:'entity', st:'live',  dom:'Social care'},
  {id:'sightline', n:'Sightline',  s:'Whether expert planning advice is followed',           spine:'place',  st:'beta',  dom:'Planning'},
  {id:'lastmile',  n:'Lastmile',   s:'Gigabit compliance for new homes',                     spine:'place',  st:'beta',  dom:'Digital'},
  {id:'bulwark',   n:'Bulwark',    s:'Who owns and maintains flood defences',                spine:'both',   st:'beta',  dom:'Environment'},
  {id:'watchman',  n:'Watchman',   s:'Insolvency exposure across public suppliers',          spine:'entity', st:'live',  dom:'Procurement'},
  {id:'compass',   n:'Compass',    s:'SEND demand forecast by neighbourhood',                spine:'place',  st:'beta',  dom:'Education'},
  {id:'baseline',  n:'Baseline',   s:'Sewage spills normalised for rainfall',                spine:'both',   st:'live',  dom:'Water'}
];
/* Sources that failed an unauthenticated request, kept visible, not hidden. */
const BLOCKED = [
  {n:'CQC syndication API',   org:'CQC',    code:401, why:'Requires a subscription key. The published location file remains free.'},
  {n:'Charity Commission API',org:'CC',     code:401, why:'Requires a registered API key. Bulk extracts stay downloadable.'},
  {n:'Bus Open Data Service', org:'DfT',    code:401, why:'Requires a free account, which the no-registration rule excludes.'},
  {n:'EPC register',          org:'MHCLG',  code:200, why:'Serves a sign-in page anonymously. Replaced by Price Paid Data.'},
  {n:'GIAS download page',    org:'DfE',    code:403, why:'Page blocks automation; the underlying CSV is directly reachable.'},
  {n:'Ofcom Connected Nations',org:'Ofcom', code:403, why:'Blocks automated retrieval. Needs a manual download step.'},
  {n:'Stat-Xplore',           org:'DWP',    code:503, why:'Requires an account for the API.'},
  {n:'Local Land Charges',    org:'HMLR',   code:403, why:'Search service blocks automation.'}
];
