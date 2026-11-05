#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
printf 'Dashboard brand: 1) Hyundai  2) Kia  Enter) Keep saved brand\n'
while :; do
    printf 'Choice: '
    read -r choice || exit 1
    case "$choice" in
        1|hyundai|Hyundai) set -- --brand hyundai; break ;;
        2|kia|Kia) set -- --brand kia; break ;;
        '') set --; break ;;
        *) printf 'Choose 1, 2, or press Enter.\n' ;;
    esac
done
exec python3 qemu/run.py --gui ccnc --state "$@"
