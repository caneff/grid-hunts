#!/bin/bash
# RSS of every solver process, every 15 s.
while true; do
  line="$(date +%H:%M:%S)"
  for p in $(pgrep -f 'zb_ba[l].py hunt|b9cove[r].py'); do
    n=$(tr '\0' ' ' < /proc/$p/cmdline | awk '{print $2" "$3" "$4}'); r=$(awk '/VmRSS/{print int($2/1024)}' /proc/$p/status)
    line="$line | $n ${r}MB"
  done
  echo "$line"; sleep 15
done
