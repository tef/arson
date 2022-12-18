test:
	python3 -m unittest discover .
build:
	python3 -m build
upload:
	python3 -m twine upload dist/*
