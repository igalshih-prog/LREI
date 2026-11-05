"""Static safety contract for a Windows-only, locally executed P3 source capture.

CI cannot assert that actual Pais HTTPS pages are available or lawfully reusable;
real captures must stay local and human-reviewed, never promoted by a test.
"""
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'LREI_capture_pais_p3_prizes_v1.ps1'


def script() -> str:
    return SCRIPT.read_text(encoding='utf-8')


def test_exact_fixed_cohort_and_pilot_default():
    src = script()
    assert '[switch]$FullCohort' in src
    assert "[string]$RepoRoot = ''" in src
    assert '@(3955..3968)' in src and '@(3955)' in src
    assert 'Get-Command py' in src
    assert 'data\\lottery.csv' in src


def test_tls_verify_redirect_and_size_bound_are_not_bypassed():
    src = script()
    assert '$req.AllowAutoRedirect = $false' in src
    assert '$response.ResponseUri.AbsoluteUri -cne $url' in src
    assert '$req.Timeout = 30000' in src
    assert '$maxPageBytes = 6MB' in src
    assert '$buffered.Length + $read -gt $MaxBytes' in src
    for unsafe in ('ServerCertificateValidationCallback', 'TrustAllCerts', 'CertificateValidationCallback', 'TlsValidation', '-SkipCertificateCheck'):
        assert unsafe not in src


def test_original_bytes_hashed_stored_in_private_user_directory():
    src = script()
    assert "Join-Path $HOME 'Downloads'" in src
    assert "WriteAllBytes($originalFile, $fetched.raw)" in src
    assert 'SHA256' in src
    assert "'xb'" not in src  # No Python-side additional copying
    assert '$req.AllowAutoRedirect = $false' in src
    assert 'Start-Sleep -Seconds 3' in src


def test_strict_offline_16_tier_parser_and_no_admission():
    src = script()
    assert 'lrei.lottery.prize_capture_intake' in src
    assert '@($candidate.candidate_tiers.regular).Count -ne 8' in src
    assert '@($candidate.candidate_tiers.double).Count -ne 8' in src
    assert '$candidate.auto_promoted_to_prize_observations -ne $false' in src
    for explicit in (
        'rows_approved_for_production = 0',
        'first_party_source_network_independently_attested = $false',
        'binding_committee_protocol_verified = $false',
        'source_use_rights_verified = $false',
        'eligible_for_play = $false',
    ):
        assert explicit in src


def test_report_sanitized_and_no_auto_git_write():
    src = script()
    assert 'private-capture-manifest.json' in src
    assert 'RAW_PAGE_CAPTURED_PARSER_FAILED_REVIEW_ONLY' in src
    assert 'CAPTURE_FAILED_PRIVATE_REVIEW_ONLY' in src
    assert 'git add' not in src and 'git push' not in src
    assert 'data/prize_observations/' not in src

def test_first_failure_stops_all_remaining_requests():
    src = script()
    # Check the failed capture/parser guard precedes the pacing/next iteration.
    guard = "if ($entry.status -ne '16_TIERS_QUARANTINED_PENDING_HUMAN_REVIEW') {"
    logging = "Write-Host ('Draw ' + $id + ': ' + $entry.status)"
    pacing = 'Start-Sleep -Seconds 3'
    assert src.count(guard) == 1
    assert src.index(logging) < src.index(guard) < src.index(pacing)
    guarded = src[src.index(guard):src.index(pacing)]
    assert '\n        break\n' in guarded
    assert 'private manifest will still be written' in guarded
