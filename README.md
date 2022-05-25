Test cricket stats
==================

This repository contains data on test cricket matches alongside data considered relevant to the match result, e.g. the ratings of the teams when each match was played. This data is intended to provide insight into which factors are most stastitically significant to the outcome of a match, and hopefully build predictive models.

The project is currently in the very early stages of development. Processed data is only available for matches between 2003-2013. Data analysis is limited to a few exploratory notebooks.

Installation
------------
First, clone the atoMEC repository and ``cd`` into the main directory.

* Recommended : using [pipenv](https://pypi.org/project/pipenv/)

  This route is recommended because `pipenv` automatically creates a virtual environment and manages dependencies.

  1. First, install `pipenv` if it is not already installed, for example via `pip install pipenv` (or see [pipenv](https://pypi.org/project/pipenv/) for    installation instructions)
  2. Install the package and its dependencies with `pipenv install`
  3. Use `pipenv shell` to activate the virtual environment
  4. To set up a Jupyter kernel for the environment: `python -m ipykernel install --user --name=test_cricket_stats`

A `requirements.txt` file is also provided (generated automatically from the `Pipfile`) for alternative installation methods.

Project Organization
------------

<p><small>The structure of this project is based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a></small></p>

Basic usage
-----------

To make the dataset, run `make data` from the home directory.

That's it so far! Feel free to have a look at the exploratory notebooks for some ideas of what can be done with the data, but so far nothing else is implemented.


Contributing
------------
Contributions are highly welcome. Please adhere to the following simple guidelines:
* Contributors should develop on branches based off of `main` and merge requests should be to `main`
* Please choose a descriptive branch name
* Python code should be formatted using [black](https://pypi.org/project/black/) style

Data sources
------------

Data is sourced from the following sources:
* [ICC historical rankings](https://web.archive.org/web/20130120040151/http://www.icc-cricket.com/match_zone/historical_ranking.php) - rankings data up to March 2013
* [Cricsheet](https://cricsheet.org/matches/) - match data from 2004 - present
* [howstat](http://www.howstat.com/cricket/home.asp) - series data

We are grateful for these data sources!
