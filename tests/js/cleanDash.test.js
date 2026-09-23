import { test } from 'node:test';
import assert from 'node:assert';

// The cleanDash helper from app/assets/platform.js
const cleanDash = s => {
  if (typeof s !== 'string') return s;
  // Handle en dash and em dash -> colon
  s = s.replace(/\s*[–—]\s*/g, ': ');
  // Handle double hyphen: colon for short qualifiers, comma for explanations
  s = s.replace(/ -- /g, (match, offset, full) => {
    const after = full.substring(offset + 4);
    const wordCount = after.split(/\s+/).length;
    const hasComplexStructure = /[.;:]/.test(after.substring(0, Math.min(50, after.length)));
    if (wordCount <= 4 && !hasComplexStructure) return ': ';
    return ', ';
  });
  return s;
};

test('cleanDash removes double hyphens, em dashes and en dashes', () => {
  // Test cases from platform.json
  const testCases = [
    {
      input: 'Get Information About Schools -- all establishments',
      expected: 'Get Information About Schools: all establishments',
      desc: 'Short qualifier should use colon'
    },
    {
      input: 'OS Linked Identifiers -- property to building',
      expected: 'OS Linked Identifiers: property to building',
      desc: 'Property descriptor should use colon'
    },
    {
      input: 'OS Linked Identifiers -- property to street',
      expected: 'OS Linked Identifiers: property to street',
      desc: 'Street descriptor should use colon'
    },
    {
      input: 'HTTP 401 -- requires a subscription key. Superseded for Groundtruth\'s purposes by cqc_hsca_locations',
      expected: 'HTTP 401, requires a subscription key. Superseded for Groundtruth\'s purposes by cqc_hsca_locations',
      desc: 'Long explanation should use comma'
    },
  ];

  testCases.forEach(({ input, expected, desc }) => {
    const result = cleanDash(input);
    assert.strictEqual(result, expected, `Failed: ${desc}\nInput: ${input}\nExpected: ${expected}\nGot: ${result}`);
  });

  // Test that no dashes remain in output
  const strings = [
    'Get Information About Schools -- all establishments',
    'OS Linked Identifiers -- property to building',
    'HTTP 401 -- requires a subscription key',
    'The test -- which was clear -- now passes',
  ];

  strings.forEach(str => {
    const result = cleanDash(str);
    assert(!result.includes('--'), `Double hyphen remained in: ${result}`);
    assert(!result.includes('–'), `En dash remained in: ${result}`); // en dash
    assert(!result.includes('—'), `Em dash remained in: ${result}`); // em dash
  });
});
