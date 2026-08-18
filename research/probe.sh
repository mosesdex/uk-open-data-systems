#!/bin/bash
# Anonymous-access probe. No keys, no cookies, no auth headers.
probe () { # id url
  code=$(curl -sL --max-time 25 -o /tmp/pb.$$ -w '%{http_code}' -A 'Mozilla/5.0 (compatible; groundtruth-audit)' "$2" 2>/dev/null)
  sz=$(wc -c < /tmp/pb.$$ 2>/dev/null | tr -d ' ')
  ct=$(file -b --mime-type /tmp/pb.$$ 2>/dev/null)
  printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$code" "$sz" "$ct" "$2"
  rm -f /tmp/pb.$$
}
export -f probe
