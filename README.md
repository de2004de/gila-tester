# Gila Test Console

A Python desktop interface adapted from the Gila test application. Run a selected check or a full set, review outcomes in a table, and save or reopen a CSV report.

## Run

Use Python 3 with Tkinter and run `python app.py`. The console opens with an empty check list. You can open a report without connecting equipment.

## Local checks

Set the environment variable `GILA_CHECKS_FILE` to the path of a trusted Python file on your own computer. The console executes this file at startup. It should define a dictionary named `checks` that maps display labels to functions. Each function takes no arguments and returns a pair containing the displayed result and a boolean indicating whether the check passed. Checks run in sequence on a background thread.

## Reports

**Save report** writes the current table to a CSV file you choose. **Open report** reads files with the same three columns in order: Check, Result, Status. Reports stay on the computer where you save them.
