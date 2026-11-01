.PHONY: test audit clean

test:
	PYTHONPATH=. python3 -m unittest discover -s tests

audit:
	python3 -m diskopt --audit

clean-dry:
	python3 -m diskopt --clean --dry-run
