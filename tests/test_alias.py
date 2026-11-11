"""Tests for Alias favorites parsing with an isolated path."""

from unittest.mock import patch

from radioactive.alias import Alias


def test_alias_value_containing_double_equals_round_trips(tmp_path):
    path = tmp_path / "alias_map"
    path.write_text("Jazz FM==http://stream/x?a=1==2\n", encoding="utf-8")

    with patch("radioactive.paths.get_alias_path", return_value=str(path)):
        alias = Alias()
        alias.generate_map()

    assert alias.alias_map == [
        {"name": "Jazz FM", "uuid_or_url": "http://stream/x?a=1==2"}
    ]
