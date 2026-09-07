#!/bin/bash
# 1-hour MVP runner
cd "$(dirname "$0")"
case "${1:---once}" in
  --once) python3 tracker.py --once ;;
  --watch) python3 tracker.py --watch ;;
  --serve) python3 tracker.py --serve ;;
  --list) python3 tracker.py --list ;;
  *) python3 tracker.py --once ;;
esac
