"""Design-specific sub-circuits for sonyx.

Two authoring modes, picked by how often the thing is instantiated:

- **Once-instantiated top blocks** (e.g. a per-band half of the die placed
  exactly once) are best as **plain functions**. The recipe cache wouldn't
  earn its keep for a single placement, and a fresh mutable return keeps the
  authoring loop fast.
- **Reusable sub-circuits placed many times** (an MZI arm, a test-structure
  ladder, a tap, a heater pair) should be ``@fw.recipe``-decorated factories,
  so their materialisation is cached/frozen and shared across placements.

Unlike the one-off top assembly in ``design.py``, everything here is meant to
be imported and composed by ``build()`` (or by other blocks).
"""
