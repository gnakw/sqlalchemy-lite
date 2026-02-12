ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
SOURCES = src

.PHONY: clean
clean:
	rm -rf build
	rm -rf dist
	rm -rf logs
	rm -rf tmp

.PHONY: format
format:
	uv run ruff check --fix $(ARGS)
	uv run ruff format $(ARGS)
	
