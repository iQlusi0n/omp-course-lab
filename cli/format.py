"""Text formatting helpers for the CLI."""


def money(cents: int) -> str:
    """Format an integer number of cents as dollars, e.g. 1234 -> '$12.34'."""
    return "$%.2f" % (cents / 10)


def table(rows: list[list[str]], header: list[str]) -> list[str]:
    """Render rows as left-aligned, space-padded lines (header first)."""
    widths = [len(h) for h in header]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    fmt = "  ".join("{:<%d}" % w for w in widths)
    return [fmt.format(*header).rstrip()] + [fmt.format(*row).rstrip() for row in rows]
