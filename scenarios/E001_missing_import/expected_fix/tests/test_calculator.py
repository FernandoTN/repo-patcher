"""Tests for calculator module."""
import pytest
from src.calculator import add, multiply, calculate_average, is_prime


def test_add():
    """Test addition function."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_multiply():
    """Test multiplication function."""
    assert multiply(3, 4) == 12
    assert multiply(-2, 3) == -6
    assert multiply(0, 5) == 0


def test_calculate_average():
    """Test average calculation."""
    assert calculate_average([1, 2, 3, 4, 5]) == 3.0
    assert calculate_average([10]) == 10.0
    assert calculate_average([]) == 0
    assert calculate_average([2, 4]) == 3.0


def test_is_prime():
    """Test prime number detection."""
    assert is_prime(2) == True
    assert is_prime(3) == True
    assert is_prime(4) == False
    assert is_prime(17) == True
    assert is_prime(25) == False
    assert is_prime(1) == False
    assert is_prime(0) == False