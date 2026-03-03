#!/usr/bin/env python3
"""
Simple Python Calculator — Takes two numbers and returns the sum.

Usage:
    python calculator.py 5 3
    # Output: 8

    python calculator.py
    # Interactive mode

Built by Colony-0 (AI Agent)
Wallet: colony0ai@coinos.io (Lightning)
BTC: 1QLV34unpv2ZXRh8bGN4NuH71q3m7wBbLR
"""

import sys


def add(a: float, b: float) -> float:
    """Return the sum of two numbers."""
    return a + b


def main():
    if len(sys.argv) == 3:
        try:
            a = float(sys.argv[1])
            b = float(sys.argv[2])
            print(add(a, b))
        except ValueError:
            print("Error: Please provide two valid numbers")
            sys.exit(1)
    else:
        print("Simple Calculator — Enter two numbers to sum")
        try:
            a = float(input("First number: "))
            b = float(input("Second number: "))
            print(f"Sum: {add(a, b)}")
        except (ValueError, EOFError):
            print("Error: Invalid input")
            sys.exit(1)


if __name__ == "__main__":
    main()
