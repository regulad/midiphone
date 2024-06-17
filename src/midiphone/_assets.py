"""Asset utilities for MIDIPhone - Reconstruct MIDI notes over a virtual device from a live audio stream.

Copyright (C) 2024  Parker Wahle

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""  # noqa: E501, B950

from __future__ import annotations

from importlib.resources import files


# The root of the package. This may not be a path if the package is installed, so just access the Traversable.
PACKAGE = files(__package__)
# If you use all of your files in a folder like `assets` or `resources` (recommended), use the following line.
RESOURCES = PACKAGE / "resources"

__all__ = ("RESOURCES",)
