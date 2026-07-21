"""Wrapped foundry / vendor IP for sonyx.

Drop external ``.gds`` files in this directory and wrap each as a leaf
Component via ``fw.import_from_gds(...)``. Label the access ports with the
``name@orientation:xs`` convention on the port layer, or pass ``ports=``
explicitly; pass ``cross_sections=`` so the wrapped ports carry the right PDK
cross-section. Wrapped IP then composes like any in-tree leaf in ``design.py``.

Example::

    from pathlib import Path

    import picasso as fw

    _HERE = Path(__file__).resolve().parent

    # Wrap the foundry-supplied phase-shifter GDS as a leaf Component:
    def vendor_phase_shifter() -> fw.Component:
        return fw.import_from_gds(
            _HERE / "vendor_phase_shifter.gds",
            cell_name="PHASE_SHIFTER",
        )
"""
