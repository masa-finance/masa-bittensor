#!/bin/bash

# Run each test file separately with coverage
python -m pytest --cov --cov-append --cov-report=html tests/test_miner.py
python -m pytest --cov --cov-append --cov-report=html tests/test_validator.py


