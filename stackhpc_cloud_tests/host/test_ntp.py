import os
import re
import pytest

MAX_OFFSET_SECONDS = 0.5  # 500 ms limit


def _get_parsed_ntp_sources():
    # fetch and parse NTP_SOURCES
    raw_ntp_sources = os.environ.get("NTP_SOURCES")
    if not raw_ntp_sources or not raw_ntp_sources.strip():
        return []
    return [s.strip() for s in raw_ntp_sources.split(",") if s.strip()]


# 1. Verify NTP_SOURCES is set
def test_ntp_sources_env_var():
    raw_ntp_sources = os.environ.get("NTP_SOURCES")
    assert (
        raw_ntp_sources is not None and raw_ntp_sources.strip() != ""
    ), "NTP_SOURCES environment variable is not set or empty."

    ntp_sources = _get_parsed_ntp_sources()
    assert ntp_sources, "NTP_SOURCES contains no valid source entries."


# 2. Check that chrony is running and syncing properly
def test_chrony_service_and_sync_status(host):
    # Check timedatectl
    timedate_stdout = host.check_output("timedatectl status")
    assert (
        "NTP service: active" in timedate_stdout
        or "System clock synchronized: yes" in timedate_stdout
    ), f"System clock is not synchronized according to timedatectl:\n{timedate_stdout}"

    # Check chrony has an active reference source marked with '*'
    sources_stdout = host.check_output("chronyc -n sources")
    active_source_match = re.search(
        r"^\^?\*\s+([^\s]+)", sources_stdout, re.MULTILINE
    )
    assert active_source_match is not None, (
        f"Chrony has no active reference source (no source marked with '*').\n"
        f"Output:\n{sources_stdout}"
    )


# 3. Check that one of the NTP_SOURCES values is actively used by chrony (*=current source)
def test_active_source_matches_expected(host):
    ntp_sources = _get_parsed_ntp_sources()
    assert ntp_sources, "Cannot verify active source because NTP_SOURCES is missing or invalid."

    sources_stdout = host.check_output("chronyc -n sources")
    active_source_match = re.search(
        r"^\^?\*\s+([^\s]+)", sources_stdout, re.MULTILINE
    )
    assert active_source_match is not None, "No active chrony source found to validate."

    active_source = active_source_match.group(1)
    is_valid_source = any(
        src in active_source or active_source in src for src in ntp_sources
    )
    assert is_valid_source, (
        f"Active chrony source '{active_source}' does not match any expected NTP_SOURCES in {ntp_sources}.\n"
        f"Chronyc Sources Output:\n{sources_stdout}"
    )


# 4. Check time offset
def test_ntp_time_offset(host):
    chrony_stdout = host.check_output("chronyc tracking")

    match = re.search(r"System time\s+:\s+([0-9.]+)\s+seconds", chrony_stdout)
    assert (
        match is not None
    ), f"Could not parse system time offset from chronyc output:\n{chrony_stdout}"

    offset = float(match.group(1))
    assert offset <= MAX_OFFSET_SECONDS, (
        f"NTP time offset {offset:.4f}s exceeds maximum threshold of {MAX_OFFSET_SECONDS}s (500ms).\n"
        f"Chronyc Tracking:\n{chrony_stdout}"
    )