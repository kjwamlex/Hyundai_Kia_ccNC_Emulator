#!/usr/bin/env python3
"""Check a candidate against this build's original engineering password hashes.

Offline only: does not change the firmware, VM, password, or retry counter.
The reconstruction was compared with hash calls from the original ARM64 HMI.
"""
import argparse
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARY = HERE / 'artifacts/ccnc-exec-audit/root/ccos/apps/hmi/engineeringmodehmi/engineeringmodehmi'
EXPECTED_BINARY_SHA256 = '5b8d1690870fa883798b2788fb16aeeb8bfd7263dce15a2785dc290188a49d14'
ENGINEERING_OFFSETS = [0x447660 + i * 0x48 for i in range(10)]


def select_hex(text):
    step = next((int(c) for c in text if c in '3456789'), 5)
    return text[step::step]


def engineering_hash(candidate):
    first = hashlib.sha256(candidate.encode('utf-8')).hexdigest()
    odd = first[1::2].encode('ascii')
    reverse_even = first[::2][::-1].encode('ascii')
    left = select_hex(hashlib.sha384(odd).hexdigest())
    right = select_hex(hashlib.sha512(reverse_even).hexdigest())
    return hashlib.sha256((left + right).encode('ascii')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate')
    parser.add_argument('--year', type=int, help='Valid head-unit clock year; omitted means invalid-clock fallback index 2')
    args = parser.parse_args()
    binary = BINARY.read_bytes()
    actual = hashlib.sha256(binary).hexdigest()
    if actual != EXPECTED_BINARY_SHA256:
        raise SystemExit(f'Unexpected HMI binary SHA-256: {actual}')
    index = 2 if args.year is None else args.year % 10
    expected = binary[ENGINEERING_OFFSETS[index]:ENGINEERING_OFFSETS[index] + 64].decode('ascii')
    result = engineering_hash(args.candidate)
    matches = [i for i, offset in enumerate(ENGINEERING_OFFSETS)
               if binary[offset:offset + 64].decode('ascii') == result]
    print(f'Engineering index: {index}')
    print(f'Engineering hash: {result}')
    print('Engineering password: ' + ('MATCH' if result == expected else 'NO MATCH'))
    print(f'Matching engineering indices: {matches}')
    dealer = hashlib.sha256(args.candidate.encode('utf-8')).hexdigest()
    print('Dealer password: ' + ('MATCH' if dealer == binary[0x447470:0x4474b0].decode('ascii') else 'NO MATCH'))
    support_match = dealer == binary[0x4474b8:0x4474f8].decode('ascii')
    print('Embedded vehicle-support hash: ' + ('MATCH' if support_match else 'NO MATCH'))
    if support_match:
        print('Vehicle-support login: DISABLED in this binary; comparison result is discarded and login returns 10')


if __name__ == '__main__':
    main()
