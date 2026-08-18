#!/bin/bash
out=probe-results.tsv; : > $out
while IFS=$'\t' read -r id url; do
  [ -z "$id" ] && continue
  (
    tmp=$(mktemp)
    code=$(curl -sL --max-time 25 -o "$tmp" -w '%{http_code}' -A 'Mozilla/5.0 (compatible; groundtruth-audit)' "$url" 2>/dev/null)
    sz=$(wc -c < "$tmp" | tr -d ' ')
    ct=$(file -b --mime-type "$tmp" 2>/dev/null)
    head1=$(head -c 100 "$tmp" | tr -d '\n\r\t' | cut -c1-60)
    printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$code" "$sz" "$ct" "$head1" >> $out
    rm -f "$tmp"
  ) &
  while [ $(jobs -r | wc -l) -ge 8 ]; do wait -n; done
done < endpoints.tsv
wait
sort -o $out $out
