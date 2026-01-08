<h1 align="center">
  <img src="https://github.com/user-attachments/assets/9442583c-e3cd-49dd-b396-d169ea0fdda4" width="500" align="center" alt="aurora-biologic logo">
</h1>

</br>

[![PyPI version](https://img.shields.io/pypi/v/aurora-biologic.svg)](https://pypi.org/project/aurora-biologic/)
[![License](https://img.shields.io/github/license/empaeconversion/aurora-biologic?color=blue)](https://github.com/empaeconversion/aurora-biologic/blob/main/LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/aurora-biologic.svg)](https://pypi.org/project/aurora-biologic/)
[![Checks](https://img.shields.io/github/actions/workflow/status/empaeconversion/aurora-biologic/test.yml)](https://github.com/EmpaEconversion/aurora-biologic/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/codecov/c/github/empaeconversion/aurora-biologic)](https://app.codecov.io/gh/EmpaEconversion/aurora-biologic)


`aurora-biologic` provides a standalone Python API and command line interface (CLI) to control Biologic cyclers.

It is designed and tested on MPG2 cyclers using EC-lab 11.52 and 11.61.

## Features
- CLI and Python API
- Connect to EC-lab cyclers
- Retrieve status of channels
- Load protocols onto channels
- Start and stop experiments

For parsing binary data from Biologic, we recommend [`yadg`](https://github.com/dgbowl/yadg).

## Installation
Install on a Windows PC with EC-lab >11.52 installed.
> [!IMPORTANT]
> EC-lab must have OLE/COM activated

OLE/COM is a Windows interface for programs to expose their functionality to third-parties, which is supported by EC-lab.

Open a terminal as administrator, go to your folder containing `EClab.exe` and register the server:

`cmd`
```cmd
cd "C:/Program files (x86)/EC-lab"
eclab \regserver
```

`powershell`
```powershell
cd "C:/Program files (x86)/EC-lab"
.\eclab \\regserver
```

You can also deregister in the same way with `/unregserver`.

Next, install this package with
```bash
pip install aurora-biologic
```

To see commands, use
```bash
biologic --help
```

The first time you run the command line, a config file is generated at:

`C:\Users\<user>\AppData\Local\aurora-biologic\aurora-biologic\config.json`

which will look like:
```json
{
    "serial_to_name": {
        "12345": "MPG2-1",
        "12346": "MPG2-2"
    },
    "eclab_path": "C:/Program Files (x86)/EC-Lab/EClab.exe"
}
```
Rename your devices according to their serial number, and make sure the EC-lab executable path is correct and the same as the executable registered in the first step.

## CLI usage

Make sure EC-lab is running.

You can check what devices and channels were found with
```bash
biologic pipelines
```
The pipeline ID is made up of the `{device name}-{channel index}`, such as `MPG2-1-7`

These IDs are used for other functions, for example to see the status of that channel use
```bash
biologic status MPG2-1-7
```

>[!TIP]
>See all commands with `biologic --help`.
>
>See details of a command with `biologic [command] --help` e.g. `biologic status --help`.

## API usage

Commands can also be run using Python.

Make sure EC-lab is running.

Then commands can be run using the BiologicAPI object
```python
from aurora_biologic import BiologicAPI
with BiologicAPI() as bio:
    bio.start(
        "my_pipeline_id",
        "path/to/my_experiment.mps",
        "path/to/an/output.mpr",
    )
```

## Using commands over SSH
>[!WARNING]
>OLE/COM requires an interactive session to function.
>
>Standard command line functions will not work in non-interactive session, such as normal SSH from a terminal.

To use the CLI over SSH you must start a listener daemon in an interactive terminal.

On the PC with EC-lab, start the listener with:
```bash
biologic daemon
```

Then from the SSH session use normal CLI commands with the `--ssh` option, e.g.
```bash
biologic status --ssh
```

Instead of trying to run OLE/COM commands directly in the non-interactive session, it will send commands to the daemon, which will execute and reply.

## Contributors

- [Graham Kimbell](https://github.com/g-kimbell)

## Acknowledgements

Special thanks to Julian Diener from Biologic for their advice and support.

This software was developed at the Laboratory of Materials for Energy Conversion at Empa, the Swiss Federal Laboratories for Materials Science and Technology, and supported by funding from the [IntelLiGent](https://heuintelligent.eu/) project from the European Union’s research and innovation program under grant agreement No. 101069765, and from the Swiss State Secretariat for Education, Research, and Innovation (SERI) under contract No. 22.001422.

<img src="https://github.com/user-attachments/assets/373d30b2-a7a4-4158-a3d8-f76e3a45a508#gh-light-mode-only" height="100" alt="IntelLiGent logo">
<img src="https://github.com/user-attachments/assets/9d003d4f-af2f-497a-8560-d228cc93177c#gh-dark-mode-only" height="100" alt="IntelLiGent logo">&nbsp;&nbsp;&nbsp;&nbsp;
<img src="https://github.com/user-attachments/assets/1d32a635-703b-432c-9d42-02e07d94e9a9" height="100" alt="EU flag">&nbsp;&nbsp;&nbsp;&nbsp;
<img src="https://github.com/user-attachments/assets/cd410b39-5989-47e5-b502-594d9a8f5ae1" height="100" alt="Swiss secretariat">
