/* Whether a postcode sector should be resolved straight to a district or
   offered as a choice depends on the raw sector, not on what survives after
   this platform's coverage is applied. A sector that genuinely spans two
   districts -- one covered, one this platform does not carry -- is still an
   ambiguous sector: the reader is owed a choice and a true disclosure, not a
   silent substitution of the one district on offer for the one they are
   actually in.

   sectorDistricts() in postcode.js reports every district a sector resolves
   to, dominant first, and stays deliberately ignorant of which of those this
   platform covers (see that file's own comment). That knowledge lives here
   instead, one level up, where it can be combined with the payload's own
   names index without teaching postcode.js anything about countries. */

export function districtChoice(allDistricts, names) {
  const all = Array.isArray(allDistricts) ? allDistricts : [];
  const isCovered = code => !!(names && names[code]);
  return {
    // More than one district in the raw sector, before any filtering, is
    // what makes a sector ambiguous -- never the count left after coverage
    // is applied.
    ambiguous: all.length > 1,
    covered: all.filter(isCovered),
    missing: all.filter(code => !isCovered(code)),
  };
}
