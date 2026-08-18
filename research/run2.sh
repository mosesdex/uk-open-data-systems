#!/bin/bash
out=probe2.tsv; : > $out
while IFS=$'\t' read -r id url hdr; do
  [ -z "$id" ] && continue
  (
    tmp=$(mktemp)
    if [ "$hdr" = "-" ] || [ -z "$hdr" ]; then
      code=$(curl -sL --max-time 25 -o "$tmp" -w '%{http_code}' "$url" 2>/dev/null)
    elif [ "$hdr" = "Mozilla/5.0" ]; then
      code=$(curl -sL --max-time 25 -o "$tmp" -w '%{http_code}' -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" "$url" 2>/dev/null)
    else
      code=$(curl -sL --max-time 25 -o "$tmp" -w '%{http_code}' -H "$hdr" "$url" 2>/dev/null)
    fi
    sz=$(wc -c < "$tmp" | tr -d ' ')
    ct=$(file -b --mime-type "$tmp" 2>/dev/null)
    printf '%s\t%s\t%s\t%s\n' "$id" "$code" "$sz" "$ct" >> $out
    rm -f "$tmp"
  ) &
done < endpoints2.tsv
wait
sort -o $out $out
