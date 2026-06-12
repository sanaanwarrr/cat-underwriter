.PHONY: install test demo ui clean

install:
	pip install -r requirements.txt
	pip install -e .

test:
	pytest

demo:
	cat-triage triage data/sample_slips/treaty_slip_hurricane_florida.md

ui:
	PYTHONPATH=src streamlit run app_streamlit.py

clean:
	rm -rf outputs/* .pytest_cache
