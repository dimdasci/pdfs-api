install:
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt

tests:
	python -m unittest discover tests 
