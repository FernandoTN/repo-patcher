package main

import "testing"

func TestFormatMessage(t *testing.T) {
    result := FormatMessage("Alice", 25)
    expected := "Hello Alice, you are 25 years old!"
    
    if result != expected {
        t.Errorf("Expected %q, got %q", expected, result)
    }
}

func TestGetGreeting(t *testing.T) {
    result := GetGreeting("Bob")
    expected := "Hello Bob"
    
    if result != expected {
        t.Errorf("Expected %q, got %q", expected, result)
    }
}