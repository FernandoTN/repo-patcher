package main

// FormatMessage formats a message with the given name and age
// This function uses fmt.Sprintf but doesn't import fmt - causing undefined error
func FormatMessage(name string, age int) string {
    return fmt.Sprintf("Hello %s, you are %d years old!", name, age)
}

// GetGreeting returns a simple greeting
func GetGreeting(name string) string {
    return "Hello " + name
}