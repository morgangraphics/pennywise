.PHONY: help install install-dev clean build release test pytest format

# Default target
help:
	@echo "Pennywise Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make install      - Install runtime dependencies"
	@echo "  make install-dev  - Install development dependencies (includes runtime deps)"
	@echo "  make build        - Build the executable with PyInstaller"
	@echo "  make release      - Create a clean release build"
	@echo "  make clean        - Remove build artifacts"
	@echo "  make test         - Run a test conversion"
	@echo "  make pytest       - Run pytest test suite"
	@echo "  make format       - Format code with Black"

# Install runtime dependencies only
install:
	pip install -r requirements.txt

# Install development dependencies (includes runtime deps)
install-dev: install
	pip install pyinstaller pytest black

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf __pycache__/
	rm -f *.spec

# Build the executable
build:
	pyinstaller --onefile \
		--name pennywise \
		--add-data "penny_database.py:." \
		penny_parser.py

# Create a release (clean + build)
release: clean build
	@echo ""
	@echo "============================================"
	@echo "Release build complete!"
	@echo "Executable location: dist/pennywise"
	@echo "============================================"
	@echo ""
	@echo "Test with:"
	@echo "  ./dist/pennywise -i ./pennies/labels/ca.docx -o test.csv"

# Test the built executable
test: build
	./dist/pennywise -i ./pennies/labels/ca.docx -o test_output.csv
	@echo "Test complete! Check test_output.csv"

# Run pytest test suite
pytest:
	python -m pytest tests/ -v

# Format code with Black
format:
	black penny_parser.py penny_database.py tests/

