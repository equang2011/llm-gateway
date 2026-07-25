.PHONY: run check

run:
	uvicorn app.main:app --reload

check:
	ruff format --check
	ruff check .
	pytest