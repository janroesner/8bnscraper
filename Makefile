# Makefile for 8-bit News Scraper

.DEFAULT_GOAL := help
.PHONY: help install new run summary open markdown

# Display help
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  help           Show this help message"
	@echo "  install        Install dependencies"
	@echo "  new            Create a new run directory"
	@echo "  run            Run the scraper"
	@echo "  summary        Summarize articles in the newest run directory"
	@echo "  open           Open the RSS feed in the newest run directory"
	@echo "  markdown       Generate a Markdown file from the articles in the newest run directory"
	@echo "  cd             Change into the current data folder"

# Install dependencies
install:
	pip install -r requirements.txt

# Create new run directory
new:
	python scrape.py -n

# Run the scraper
run:
	python scrape.py

# Summarize articles in newest run directory
summary:
	python scrape.py -s

# Open RSS feed in newest run directory
open:
	python scrape.py -o

# Generate Markdown file from articles in newest run directory
markdown:
	python scrape.py -m

# Change into the latest data folder
cd:
	open `find data -type d -name "run_*" | sort | tail -n 1`