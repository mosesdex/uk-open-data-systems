/* The app is built from classic scripts that assign globals. The pure logic
   lives in modules so the test runner can import it directly, and this entry is
   the one bridge between the two: it runs deferred, before DOMContentLoaded, so
   the router finds it by the time any route is handled. */
import { canonicalHash, ROUTER_HEADS, firstServable } from './routes.js';
import { matchPlaces, looksLikePostcode } from './places.js';
import { placeSummary } from './summary.js';
import { unusualRows } from './unusual.js';

window.GT_LIB = Object.assign(window.GT_LIB || {},
  { canonicalHash, ROUTER_HEADS, firstServable, matchPlaces, looksLikePostcode, placeSummary, unusualRows });
