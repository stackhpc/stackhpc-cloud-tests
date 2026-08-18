import os
import re
import subprocess

MAX_OFFSET_SECONDS = 0.5  # 500 ms limit


def test_ntp_configuration_and_sync():
    raw_ntp_sources = os.environ.get("NTP_SOURCES")

    # 1. Verify NTP_SOURCES environment variable and parse into a list
    assert (
        raw_ntp_sources is not None and raw_ntp_sources.strip() != ""
    ), "NTP_SOURCES environment variable is not set or empty."

    # Split comma-separated string into a clean list of individual source hosts/IPs
    ntp_sources = [s.strip() for s in raw_ntp_sources.split(",") if s.strip()]
    assert ntp_sources, "NTP_SOURCES contains no valid source entries."

    # 2. Basic service check via timedatectl
    timedate_res = subprocess.run(
        ["timedatectl", "status"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert (
        "NTP service: active" in timedate_res.stdout
        or "System clock synchronized: yes" in timedate_res.stdout
    ), f"System clock is not synchronized according to timedatectl:\n{timedate_res.stdout}"

    # 3. Check that one of the NTP_SOURCES values is actively used by chrony (* = current synchronized source)
    sources_res = subprocess.run(
        ["chronyc", "-n", "sources"],
        capture_output=True,
        text=True,
        check=True,
    )

    # In 'chronyc sources', the line starting with '*' or '^*' indicates the active reference source.
    active_source_match = re.search(
        r"^\^?\*\s+([^\s]+)", sources_res.stdout, re.MULTILINE
    )
    assert active_source_match is not None, (
        f"Chrony has no active reference source (no source marked with '*').\n"
        f"Output:\n{sources_res.stdout}"
    )

    active_source = active_source_match.group(1)

    # Validate that active_source matches ANY server in your ntp_sources list
    is_valid_source = any(
        src in active_source or active_source in src for src in ntp_sources
    )
    assert is_valid_source, (
        f"Active chrony source '{active_source}' does not match any expected NTP_SOURCES in {ntp_sources}.\n"
        f"Chronyc Sources Output:\n{sources_res.stdout}"
    )

    # 4. Check exact time offset using chronyc tracking
    chrony_res = subprocess.run(
        ["chronyc", "tracking"],
        capture_output=True,
        text=True,
        check=True,
    )

    # Output line example: "System time     : 0.000012345 seconds slow of NTP time"
    match = re.search(r"System time\s+:\s+([0-9.]+)\s+seconds", chrony_res.stdout)
    assert (
        match is not None
    ), f"Could not parse system time offset from chronyc output:\n{chrony_res.stdout}"

    offset = float(match.group(1))
    assert offset <= MAX_OFFSET_SECONDS, (
        f"NTP time offset {offset:.4f}s exceeds maximum threshold of {MAX_OFFSET_SECONDS}s (500ms).\n"
        f"Chronyc Tracking:\n{chrony_res.stdout}"
    )
