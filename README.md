# Icy Hot Waters

## Work Heavily In Progress, however, development is paused during the ratings period of the jam this was originally made for.

## Launching the game using CLI
After going through the entire process, 
subsequent launches are a simple `python icy_hot_waters.py` 
from the `IcyHotWaters` directory.

It's important to install the requirements with the specified `pygame-ce` version `2.4.1`
as this project uses API that might be deprecated in later releases and may not exist
yet in earlier ones.

### On Windows
```
git clone https://github.com/Matiiss/IcyHotWaters
cd ./IcyHotWaters
py -m venv venv
./venv/scripts/activate
pip install -r requirements.txt
python icy_hot_waters.py
```

### On Linux
```
git clone https://github.com/Matiiss/IcyHotWaters
cd ./IcyHotWaters
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
python icy_hot_waters.py
```
