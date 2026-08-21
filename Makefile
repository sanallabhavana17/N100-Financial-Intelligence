.PHONY: load ratios test report dashboard api clean

load:
	python -m src.etl.loader

ratios:
	python -m src.etl.ratios

test:
	pytest -q

report:
	python -m src.report

dashboard:
	python -m src.dashboard

api:
	python -m src.api

clean:
	python -m src.clean