# Before starting

## Install the virtual environment
First, make sure you create a virtual environment for this project (use `venv` preferably).

Then, open the VS Code terminal and type:

`.\.venv\Scripts\Activate.ps1`

This will launch the activation script through Powershell. If you get an execution error because the script execution is deactivated on your device, then:

1. Open a Powershell terminal as administrator
2. Type `set-executionpolicy unrestricted`
3. Re-launch your activation script.

All needed packages are listed in the `requirements.txt` file. To install them, type on the VS Code terminal:

`python.exe -m pip install -r requirements.txt`
