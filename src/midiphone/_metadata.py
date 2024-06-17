"""Metadata for MIDIPhone - Reconstruct MIDI notes over a virtual device from a live audio stream.

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

import logging


try:
    from importlib.metadata import PackageMetadata
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import metadata as __load
except ImportError:  # pragma: no cover
    from importlib_metadata import PackageMetadata  # type: ignore
    from importlib_metadata import PackageNotFoundError  # type: ignore
    from importlib_metadata import metadata as __load  # type: ignore


logger = logging.getLogger(__package__)
try:
    metadata: PackageMetadata = __load(__package__)
    __uri__ = metadata["home-page"]
    __title__ = metadata["name"]
    __summary__ = metadata["summary"]
    __license__ = metadata["license"]
    __version__ = metadata["version"]
    __author__ = metadata["author"]
    __maintainer__ = metadata["maintainer"]
    __contact__ = metadata["maintainer"]
except PackageNotFoundError:  # pragma: no cover
    logger.error(f"Could not load package metadata for {__package__}. Is it installed?")
    logger.debug("Falling back to static metadata.")
    __uri__ = ""
    __title__ = "MIDIPhone"
    __summary__ = "Reconstruct MIDI notes over a virtual device from a live audio stream"
    __license__ = "GPL-3.0"
    __version__ = "0.0.0"
    __author__ = "Parker Wahle"
    __maintainer__ = "Parker Wahle"
    __contact__ = "Parker Wahle"
__copyright__ = "Copyright 2024"


__all__ = (
    "__copyright__",
    "__uri__",
    "__title__",
    "__summary__",
    "__license__",
    "__version__",
    "__author__",
    "__maintainer__",
    "__contact__",
)
