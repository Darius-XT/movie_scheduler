from unittest.mock import Mock

import pytest

import movie_scheduler.shared.maoyan_diagnostics as diagnostics


def test_page_diagnostics_omits_body_and_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    warning = Mock()
    monkeypatch.setattr(diagnostics.logger, "warning", warning)
    diagnostics.log_page_diagnostics(
        "cinema_shows_empty",
        '<title>secret-title</title><script>cookie=secret-cookie</script>'
        '<div class="show-list"><table class="plist"><tr><td>'
        '<a href="/xseats/123?token=secret-token">secret-body</a></td></tr></table></div>',
        movie_id=12, cinema_id=34,
    )
    rendered = str(warning.call_args)
    assert '"show_rows": 1' in rendered
    assert '"seat_links": 1' in rendered
    assert '"movie_id": 12' in rendered
    assert "secret-" not in rendered


def test_exception_frames_omits_exception_message() -> None:
    try:
        raise RuntimeError("https://verify.example/?token=secret-token")
    except RuntimeError as error:
        frames = diagnostics.safe_exception_frames(error)
    assert "test_exception_frames_omits_exception_message" in frames
    assert "secret-token" not in frames
