# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

import shutil
from importlib import reload
from pathlib import Path

import coreason_economist.utils.logger as logger_module
from coreason_economist.utils.logger import logger


def test_logger_initialization() -> None:
    """Test that the logger is initialized correctly and creates the log directory."""
    # Force removal of logs directory to test creation
    log_path = Path("logs")
    if log_path.exists():
        shutil.rmtree(log_path)

    # Reload module to trigger execution of module-level code
    reload(logger_module)

    assert log_path.exists()
    assert log_path.is_dir()


def test_logger_exports() -> None:
    """Test that logger is exported."""
    assert logger is not None
