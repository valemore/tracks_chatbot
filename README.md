# Dependencies
The bot has three dependencies (inflect, python-Levenshtein, fuzzywuzzy), used for recognizing numbers given as text, and doing fuzzy matching.

Install via
```
pip install inflect, python-Levenshtein, fuzzywuzzy
```
or create a conda environment
```
conda env create -f tracks_chatbot.yml
conda activate tracks_chatbot.yml
```

# Running
Start a session via
```
python run.py
```

Chat logs and data is saved in the working directory.

# Demo
You can try out the demo sessions
```
python run.py < Demo1.txt
```
and
```
python run.py < Demo2.txt
```
that show some of the bot's flexibility.
