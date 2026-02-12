.PHONY: help install clean build release test

# Default target
help:
	@echo "Pennywise Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make install    - Install development dependencies"
	@echo "  make build      - Build the executable with PyInstaller"
	@echo "  make release    - Create a clean release build"
	@echo "  make clean      - Remove build artifacts"
	@echo "  make test       - Run a test conversion"

# Install dependencies
install:
	pip install -r requirements.txt
	pip install pyinstaller

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
