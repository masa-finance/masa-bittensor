#!/bin/bash

# Run each test file separately with coverage
python -m coverage run -m unittest tests/test_validator.py
python -m coverage run -m unittest tests/test_miner.py

# Combine the coverage data
python -m coverage combine
python -m coverage report
