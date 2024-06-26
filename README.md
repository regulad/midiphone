# MIDIPhone

[![PyPI](https://img.shields.io/pypi/v/midiphone.svg)][pypi status]
[![Status](https://img.shields.io/pypi/status/midiphone.svg)][pypi status]
[![Python Version](https://img.shields.io/pypi/pyversions/midiphone)][pypi status]
[![License](https://img.shields.io/pypi/l/midiphone)][license]

[![Read the documentation at https://midiphone.readthedocs.io/](https://img.shields.io/readthedocs/midiphone/latest.svg?label=Read%20the%20Docs)][read the docs]
[![Tests](https://github.com/regulad/midiphone/workflows/Tests/badge.svg)][tests]
[![Codecov](https://codecov.io/gh/regulad/midiphone/branch/main/graph/badge.svg)][codecov]

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)][pre-commit]
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)][black]

[pypi status]: https://pypi.org/project/midiphone/
[read the docs]: https://midiphone.readthedocs.io/
[tests]: https://github.com/regulad/midiphone/actions?workflow=Tests
[codecov]: https://app.codecov.io/gh/regulad/midiphone
[pre-commit]: https://github.com/pre-commit/pre-commit
[black]: https://github.com/psf/black

![IMG_1970.mov](IMG_1970.mov)

![IMG_1972.mov](IMG_1972.mov)

## Features

- Reconstruct a MIDI port from an audio input
- Buttons to help adjust sensitivity
- Saved config between sessions

## Requirements

- https://www.tobias-erichsen.de/software/loopmidi.html
- Some way to get your piano's audio into your computer (line in preferred)
- Python 3.11+
- Windows 10+ (for now; other OSes possibly added later)
- A sine wave voice on your piano (or a similar sound) (optional; but works best with it)
  - My Yamaha PSR-E253 has a Sine wave on Voice 193, works well from C4-C5; iffy in other octaves

## Installation

#### EXE is on Releases page; you can use that if you don't want to install Python

You can install _MIDIPhone_ via [pip] from [PyPI]:

```console
$ pip install midiphone
```

## Usage

Please see the [Command-line Reference] for details.

## Contributing

Contributions are very welcome.
To learn more, see the [Contributor Guide].

## License

Distributed under the terms of the [GPL 3.0 license][license],
_MIDIPhone_ is free and open source software.

## Issues

If you encounter any problems,
please [file an issue] along with a detailed description.

## Credits

This project was generated from [@regulad]'s [neopy] template.

[@regulad]: https://github.com/regulad
[pypi]: https://pypi.org/
[neopy]: https://github.com/regulad/cookiecutter-neopy
[file an issue]: https://github.com/regulad/midiphone/issues
[pip]: https://pip.pypa.io/

<!-- github-only -->

[license]: https://github.com/regulad/midiphone/blob/main/LICENSE
[contributor guide]: https://github.com/regulad/midiphone/blob/main/CONTRIBUTING.md
[command-line reference]: https://midiphone.readthedocs.io/en/latest/usage.html
