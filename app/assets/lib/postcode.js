/* Turning a typed postcode into the district it sits in.

   The index this reads is built by platform/groundtruth/postcodes.py and
   served as app/data/postcodes.json. It is keyed by sector, the outcode plus
   the first digit of the incode, which places 96.45% of postcodes by its first
   candidate. The remaining sectors span more than one district and carry all
   of them, dominant first, so the caller can ask rather than guess. */

const FULL = /^([A-Z]{1,2}\d[A-Z\d]?)\s*(\d)([A-Z]{2})$/i;

export function sectorKey(raw) {
  const m = FULL.exec(String(raw || '').trim().replace(/\s+/g, ' '));
  return m ? (m[1] + m[2]).toUpperCase() : null;
}

export function sectorDistricts(raw, index) {
  const key = sectorKey(raw);
  if (!key) return [];
  const sectors = (index && index.sectors) || null;
  if (!sectors) return [];
  const hit = sectors[key];
  return Array.isArray(hit) ? hit.slice() : [];
}
