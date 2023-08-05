PYTHON ?= python3.8

# Python Code Style
reformat:
	$(PYTHON) -m black .
stylecheck:
	$(PYTHON) -m black --check .
stylediff:
	$(PYTHON) -m black --check --diff .
