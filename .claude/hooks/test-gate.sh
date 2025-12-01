#!/bin/bash
# Spec Kit Test Gate Hook
# Runs tests after Claude edits source files (not specs/docs)
#
# This hook enforces the 100% test pass gate by running tests
# after every edit to source code files.
#
# BEHAVIOR:
# - Detects project type (Node.js, Python, Go, Rust, etc.)
# - Runs appropriate test command
# - Returns exit code (0 = pass, non-zero = fail)
# - Claude Code will see the failure and should fix before proceeding
#
# To enable, add to settings.json:
# {
#   "hooks": {
#     "PostToolUse": [{
#       "hooks": [{ "command": "./.claude/hooks/test-gate.sh \"$CLAUDE_FILE_PATHS\"", "type": "command" }],
#       "matcher": "Edit|Write|MultiEdit"
#     }]
#   }
# }

set -e

# Exit early if no file path provided
if [ -z "$1" ]; then
    exit 0
fi

FILE_PATHS="$1"

# Skip test runs for non-source files
should_run_tests() {
    local file="$1"

    # Skip spec/doc files - no tests needed
    case "$file" in
        *.md|*.txt|*.json|*.yaml|*.yml|*.toml|*.ini|*.cfg)
            return 1
            ;;
        specs/*|.specify/*|.claude/*|docs/*|README*|CHANGELOG*|LICENSE*)
            return 1
            ;;
    esac

    # Run tests for source files
    case "$file" in
        *.py|*.js|*.ts|*.jsx|*.tsx|*.go|*.rs|*.rb|*.java|*.kt|*.swift|*.c|*.cpp|*.h)
            return 0
            ;;
    esac

    return 1
}

# Check if any file in the list needs tests
needs_tests=false
for file in $FILE_PATHS; do
    if should_run_tests "$file"; then
        needs_tests=true
        break
    fi
done

if [ "$needs_tests" = false ]; then
    exit 0
fi

# Detect project type and run appropriate tests
run_tests() {
    local test_cmd=""
    local test_result=0

    # Node.js / JavaScript / TypeScript
    if [ -f "package.json" ]; then
        if grep -q '"test"' package.json 2>/dev/null; then
            echo "🧪 Running: npm test"
            npm test --silent 2>&1 || test_result=$?
            return $test_result
        fi
    fi

    # Python
    if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "pytest.ini" ] || [ -d "tests" ]; then
        if command -v pytest &> /dev/null; then
            echo "🧪 Running: pytest"
            pytest --tb=short -q 2>&1 || test_result=$?
            return $test_result
        elif command -v python &> /dev/null; then
            echo "🧪 Running: python -m pytest"
            python -m pytest --tb=short -q 2>&1 || test_result=$?
            return $test_result
        fi
    fi

    # Go
    if [ -f "go.mod" ]; then
        echo "🧪 Running: go test ./..."
        go test ./... 2>&1 || test_result=$?
        return $test_result
    fi

    # Rust
    if [ -f "Cargo.toml" ]; then
        echo "🧪 Running: cargo test"
        cargo test 2>&1 || test_result=$?
        return $test_result
    fi

    # Ruby
    if [ -f "Gemfile" ]; then
        if [ -f "Rakefile" ] && grep -q "test" Rakefile 2>/dev/null; then
            echo "🧪 Running: bundle exec rake test"
            bundle exec rake test 2>&1 || test_result=$?
            return $test_result
        elif command -v rspec &> /dev/null; then
            echo "🧪 Running: bundle exec rspec"
            bundle exec rspec 2>&1 || test_result=$?
            return $test_result
        fi
    fi

    # Java / Maven
    if [ -f "pom.xml" ]; then
        echo "🧪 Running: mvn test"
        mvn test -q 2>&1 || test_result=$?
        return $test_result
    fi

    # Java / Gradle
    if [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
        echo "🧪 Running: ./gradlew test"
        ./gradlew test --quiet 2>&1 || test_result=$?
        return $test_result
    fi

    # No test framework detected - skip silently
    echo "⚠️  No test framework detected - skipping test gate"
    return 0
}

# Run tests and capture result
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 TEST GATE: Verifying 100% pass rate"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if run_tests; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ TEST GATE PASSED: All tests pass"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ TEST GATE FAILED: Fix failing tests before proceeding"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi
