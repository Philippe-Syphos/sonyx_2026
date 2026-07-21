"""Smoke tests for the sonyx layout."""

from sonyx import layout


def test_materializes_and_validates():
    """The layout builds and passes framework validation."""
    layout.materialize()
    layout.validate()


def test_writes_gds(tmp_path):
    """The layout writes a GDS file."""
    out = tmp_path / "sonyx.gds"
    layout.write_gds(out)
    assert out.exists()
