PYTHON ?= python3.8

# Python Code Style
reformat:
	$(PYTHON) -m black -l 99 .
stylecheck:
	$(PYTHON) -m black --check -l 99 .
stylediff:
	$(PYTHON) -m black --check --diff -l 99 .