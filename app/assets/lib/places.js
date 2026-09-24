/* The front page takes a council or district name. The payload ships
   places.names, 318 of them, which is the whole index this needs.

   A typed postcode is resolved by postcode.js against a sector index served
   separately, so this module stays the name index and nothing more. */

const POSTCODE = /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i;

export function looksLikePostcode(query) {
  return POSTCODE.test(String(query || '').trim());
}

export function matchPlaces(query, names, limit = 8) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return [];

  const exact = [], starts = [], contains = [];
  for (const [code, name] of Object.entries(names || {})) {
    const n = String(name).toLowerCase();
    if (n === q) exact.push({ code, name });
    else if (n.startsWith(q)) starts.push({ code, name });
    else if (n.includes(q)) contains.push({ code, name });
  }
  const byName = (a, b) => a.name.localeCompare(b.name, 'en-GB');
  return [...exact.sort(byName), ...starts.sort(byName), ...contains.sort(byName)].slice(0, limit);
}
