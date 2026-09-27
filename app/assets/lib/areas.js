/* Region and combined authority search. payload.areas ships about 20 of
   them, keyed by ONS code, each carrying a name, a kind ('region' or
   'combined authority') and the districts inside it.

   West Midlands, East Midlands and North East are each both a region and a
   combined authority, covering different districts -- so unlike matchPlaces,
   this never stops at the first hit for a name: every colliding match comes
   back, labelled by kind, and the caller decides how to show both rather
   than one silently winning over the other. */

export function matchAreas(query, areas, limit = 8) {
  const q = String(query || '').trim().toLowerCase();
  if (!q || !areas) return [];

  const exact = [], starts = [], contains = [];
  for (const [code, area] of Object.entries(areas)) {
    if (!area || !area.name) continue;
    const n = String(area.name).toLowerCase();
    const hit = { code, name: area.name, kind: area.kind, districts: area.districts || [] };
    if (n === q) exact.push(hit);
    else if (n.startsWith(q)) starts.push(hit);
    else if (n.includes(q)) contains.push(hit);
  }
  const byName = (a, b) => a.name.localeCompare(b.name, 'en-GB');
  return [...exact.sort(byName), ...starts.sort(byName), ...contains.sort(byName)].slice(0, limit);
}

export function areaDistricts(code, areas) {
  if (!areas || !areas[code]) return [];
  return areas[code].districts || [];
}
