from __future__ import annotations


def compare_benchmarks(before: dict, after: dict) -> str:
    if not before or not after:
        return "Benchmark-Daten fehlen."

    ram_diff = before["ram_percent"] - after["ram_percent"]
    cpu_diff = before.get("cpu_percent", 0) - after.get("cpu_percent", 0)
    disk_diff = after["disk_free_gb"] - before["disk_free_gb"]

    return (
        "✅ Benchmark-Vergleich\n"
        f"Vorher:  RAM {before['ram_percent']:.1f}% | CPU {before.get('cpu_percent', 0):.1f}% | Disk frei {before['disk_free_gb']:.1f} GB\n"
        f"Nachher: RAM {after['ram_percent']:.1f}% | CPU {after.get('cpu_percent', 0):.1f}% | Disk frei {after['disk_free_gb']:.1f} GB\n\n"
        "Verbesserung:\n"
        f"• RAM: {'✅ ' if ram_diff > 0 else '⚠️ '}{ram_diff:+.1f}%\n"
        f"• CPU: {'✅ ' if cpu_diff > 0 else '⚠️ '}{cpu_diff:+.1f}%\n"
        f"• Disk frei: {disk_diff:+.1f} GB"
    )
