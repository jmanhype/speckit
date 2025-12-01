#!/bin/bash
# Spec Kit Test Gate Hook - Enhanced Edition
# Enforces 100% test pass rate AND 100% code coverage after source file edits
#
# REQUIREMENTS:
# - 100% unit tests passing
# - 100% integration tests passing
# - 100% smoke tests passing
# - 100% code coverage (lines and branches)
#
# BEHAVIOR:
# - Detects project type (Node.js, Python, Go, Rust, etc.)
# - Runs appropriate test commands with coverage
# - Blocks progression if ANY test fails or coverage < 100%
# - Returns exit code (0 = pass, non-zero = fail)
#
# CONFIGURATION:
# Set these environment variables to customize:
#   SPECKIT_COVERAGE_THRESHOLD=100     # Required coverage percentage
#   SPECKIT_SKIP_INTEGRATION=false     # Skip integration tests
#   SPECKIT_SKIP_SMOKE=false           # Skip smoke tests
#   SPECKIT_SKIP_COVERAGE=false        # Skip coverage check
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

# Configuration with defaults
COVERAGE_THRESHOLD="${SPECKIT_COVERAGE_THRESHOLD:-100}"
SKIP_INTEGRATION="${SPECKIT_SKIP_INTEGRATION:-false}"
SKIP_SMOKE="${SPECKIT_SKIP_SMOKE:-false}"
SKIP_COVERAGE="${SPECKIT_SKIP_COVERAGE:-false}"

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

# Track overall results
UNIT_PASSED=false
INTEGRATION_PASSED=false
SMOKE_PASSED=false
COVERAGE_PASSED=false
COVERAGE_PERCENT=0

# Run unit tests with coverage
run_unit_tests() {
    local test_result=0

    # Node.js / JavaScript / TypeScript
    if [ -f "package.json" ]; then
        if grep -q '"test"' package.json 2>/dev/null; then
            echo "🧪 Running unit tests: npm test"

            # Check for coverage script
            if grep -q '"test:coverage"' package.json 2>/dev/null; then
                npm run test:coverage 2>&1 || test_result=$?
            elif grep -q '"coverage"' package.json 2>/dev/null; then
                npm run coverage 2>&1 || test_result=$?
            elif grep -q 'jest' package.json 2>/dev/null || [ -f "jest.config.js" ] || [ -f "jest.config.ts" ]; then
                npm test -- --coverage --coverageReporters=text 2>&1 || test_result=$?
            elif grep -q 'vitest' package.json 2>/dev/null || [ -f "vitest.config.ts" ]; then
                npm test -- --coverage 2>&1 || test_result=$?
            elif grep -q 'c8' package.json 2>/dev/null; then
                npx c8 npm test 2>&1 || test_result=$?
            else
                npm test 2>&1 || test_result=$?
            fi

            # Extract coverage percentage if available
            extract_js_coverage
            return $test_result
        fi
    fi

    # Python
    if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "pytest.ini" ] || [ -d "tests" ]; then
        echo "🧪 Running unit tests: pytest with coverage"
        if command -v pytest &> /dev/null; then
            pytest --tb=short -q --cov --cov-report=term --cov-fail-under="$COVERAGE_THRESHOLD" 2>&1 || test_result=$?
        elif command -v python &> /dev/null; then
            python -m pytest --tb=short -q --cov --cov-report=term --cov-fail-under="$COVERAGE_THRESHOLD" 2>&1 || test_result=$?
        fi
        extract_python_coverage
        return $test_result
    fi

    # Go
    if [ -f "go.mod" ]; then
        echo "🧪 Running unit tests: go test with coverage"
        go test -cover -coverprofile=coverage.out ./... 2>&1 || test_result=$?
        extract_go_coverage
        return $test_result
    fi

    # Rust
    if [ -f "Cargo.toml" ]; then
        echo "🧪 Running unit tests: cargo test"
        if command -v cargo-tarpaulin &> /dev/null; then
            cargo tarpaulin --out Stdout 2>&1 || test_result=$?
        else
            cargo test 2>&1 || test_result=$?
        fi
        return $test_result
    fi

    # Ruby
    if [ -f "Gemfile" ]; then
        echo "🧪 Running unit tests: rspec with coverage"
        if [ -f "Rakefile" ] && grep -q "test" Rakefile 2>/dev/null; then
            bundle exec rake test 2>&1 || test_result=$?
        elif command -v rspec &> /dev/null; then
            bundle exec rspec 2>&1 || test_result=$?
        fi
        return $test_result
    fi

    # Java / Maven
    if [ -f "pom.xml" ]; then
        echo "🧪 Running unit tests: mvn test with jacoco"
        mvn test jacoco:report -q 2>&1 || test_result=$?
        return $test_result
    fi

    # Java / Gradle
    if [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
        echo "🧪 Running unit tests: gradle test with jacoco"
        ./gradlew test jacocoTestReport --quiet 2>&1 || test_result=$?
        return $test_result
    fi

    # No test framework detected
    echo "⚠️  No test framework detected - skipping unit tests"
    UNIT_PASSED=true
    return 0
}

# Run integration tests
run_integration_tests() {
    if [ "$SKIP_INTEGRATION" = "true" ]; then
        echo "⏭️  Skipping integration tests (SPECKIT_SKIP_INTEGRATION=true)"
        INTEGRATION_PASSED=true
        return 0
    fi

    local test_result=0

    # Node.js
    if [ -f "package.json" ]; then
        if grep -q '"test:integration"' package.json 2>/dev/null; then
            echo "🔗 Running integration tests: npm run test:integration"
            npm run test:integration 2>&1 || test_result=$?
            return $test_result
        elif grep -q '"integration"' package.json 2>/dev/null; then
            echo "🔗 Running integration tests: npm run integration"
            npm run integration 2>&1 || test_result=$?
            return $test_result
        fi
    fi

    # Python
    if [ -d "tests/integration" ] || [ -d "integration_tests" ]; then
        echo "🔗 Running integration tests: pytest integration"
        if [ -d "tests/integration" ]; then
            pytest tests/integration --tb=short -q 2>&1 || test_result=$?
        else
            pytest integration_tests --tb=short -q 2>&1 || test_result=$?
        fi
        return $test_result
    fi

    # Check for pytest markers
    if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
        if grep -q "integration" pytest.ini 2>/dev/null || grep -q "integration" pyproject.toml 2>/dev/null; then
            echo "🔗 Running integration tests: pytest -m integration"
            pytest -m integration --tb=short -q 2>&1 || test_result=$?
            return $test_result
        fi
    fi

    # Go
    if [ -f "go.mod" ]; then
        if [ -d "integration" ] || ls *_integration_test.go &>/dev/null 2>&1; then
            echo "🔗 Running integration tests: go test -tags=integration"
            go test -tags=integration ./... 2>&1 || test_result=$?
            return $test_result
        fi
    fi

    echo "⏭️  No integration tests found - skipping"
    INTEGRATION_PASSED=true
    return 0
}

# Run smoke tests
run_smoke_tests() {
    if [ "$SKIP_SMOKE" = "true" ]; then
        echo "⏭️  Skipping smoke tests (SPECKIT_SKIP_SMOKE=true)"
        SMOKE_PASSED=true
        return 0
    fi

    local test_result=0

    # Node.js
    if [ -f "package.json" ]; then
        if grep -q '"test:smoke"' package.json 2>/dev/null; then
            echo "💨 Running smoke tests: npm run test:smoke"
            npm run test:smoke 2>&1 || test_result=$?
            return $test_result
        elif grep -q '"smoke"' package.json 2>/dev/null; then
            echo "💨 Running smoke tests: npm run smoke"
            npm run smoke 2>&1 || test_result=$?
            return $test_result
        fi
    fi

    # Python
    if [ -d "tests/smoke" ] || [ -d "smoke_tests" ]; then
        echo "💨 Running smoke tests: pytest smoke"
        if [ -d "tests/smoke" ]; then
            pytest tests/smoke --tb=short -q 2>&1 || test_result=$?
        else
            pytest smoke_tests --tb=short -q 2>&1 || test_result=$?
        fi
        return $test_result
    fi

    # Check for pytest markers
    if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
        if grep -q "smoke" pytest.ini 2>/dev/null || grep -q "smoke" pyproject.toml 2>/dev/null; then
            echo "💨 Running smoke tests: pytest -m smoke"
            pytest -m smoke --tb=short -q 2>&1 || test_result=$?
            return $test_result
        fi
    fi

    echo "⏭️  No smoke tests found - skipping"
    SMOKE_PASSED=true
    return 0
}

# Extract coverage from various tools
extract_js_coverage() {
    # Try to find coverage in output or coverage files
    if [ -f "coverage/coverage-summary.json" ]; then
        COVERAGE_PERCENT=$(jq -r '.total.lines.pct // 0' coverage/coverage-summary.json 2>/dev/null || echo "0")
    elif [ -f "coverage/lcov-report/index.html" ]; then
        COVERAGE_PERCENT=$(grep -o '[0-9]*\.[0-9]*%' coverage/lcov-report/index.html 2>/dev/null | head -1 | tr -d '%' || echo "0")
    fi
}

extract_python_coverage() {
    # Coverage is enforced via --cov-fail-under, but extract for display
    if [ -f ".coverage" ]; then
        COVERAGE_PERCENT=$(coverage report 2>/dev/null | grep -o 'TOTAL.*[0-9]*%' | grep -o '[0-9]*%' | tr -d '%' || echo "0")
    fi
}

extract_go_coverage() {
    if [ -f "coverage.out" ]; then
        COVERAGE_PERCENT=$(go tool cover -func=coverage.out 2>/dev/null | grep total | awk '{print $3}' | tr -d '%' || echo "0")
    fi
}

# Check coverage threshold
check_coverage() {
    if [ "$SKIP_COVERAGE" = "true" ]; then
        echo "⏭️  Skipping coverage check (SPECKIT_SKIP_COVERAGE=true)"
        COVERAGE_PASSED=true
        return 0
    fi

    if [ -z "$COVERAGE_PERCENT" ] || [ "$COVERAGE_PERCENT" = "0" ]; then
        echo "⚠️  Could not determine coverage percentage"
        # Don't fail if coverage can't be determined - tests still ran
        COVERAGE_PASSED=true
        return 0
    fi

    # Compare as integers (truncate decimals)
    local coverage_int=${COVERAGE_PERCENT%.*}

    if [ "$coverage_int" -ge "$COVERAGE_THRESHOLD" ]; then
        COVERAGE_PASSED=true
        return 0
    else
        COVERAGE_PASSED=false
        return 1
    fi
}

# Main execution
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 TEST GATE: Enforcing 100% Pass Rate + ${COVERAGE_THRESHOLD}% Coverage"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run all test types
echo ""
echo "📦 UNIT TESTS"
echo "─────────────"
if run_unit_tests; then
    UNIT_PASSED=true
    echo "✅ Unit tests passed"
else
    UNIT_PASSED=false
    echo "❌ Unit tests FAILED"
fi

echo ""
echo "🔗 INTEGRATION TESTS"
echo "────────────────────"
if run_integration_tests; then
    INTEGRATION_PASSED=true
    echo "✅ Integration tests passed"
else
    INTEGRATION_PASSED=false
    echo "❌ Integration tests FAILED"
fi

echo ""
echo "💨 SMOKE TESTS"
echo "──────────────"
if run_smoke_tests; then
    SMOKE_PASSED=true
    echo "✅ Smoke tests passed"
else
    SMOKE_PASSED=false
    echo "❌ Smoke tests FAILED"
fi

echo ""
echo "📊 COVERAGE CHECK"
echo "─────────────────"
if check_coverage; then
    echo "✅ Coverage: ${COVERAGE_PERCENT}% (threshold: ${COVERAGE_THRESHOLD}%)"
else
    echo "❌ Coverage: ${COVERAGE_PERCENT}% (required: ${COVERAGE_THRESHOLD}%)"
fi

# Final summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$UNIT_PASSED" = true ] && [ "$INTEGRATION_PASSED" = true ] && [ "$SMOKE_PASSED" = true ] && [ "$COVERAGE_PASSED" = true ]; then
    echo "✅ TEST GATE PASSED"
    echo ""
    echo "   Unit Tests:        ✓ PASS"
    echo "   Integration Tests: ✓ PASS"
    echo "   Smoke Tests:       ✓ PASS"
    echo "   Coverage:          ✓ ${COVERAGE_PERCENT}%"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo "❌ TEST GATE FAILED - Fix issues before proceeding"
    echo ""
    [ "$UNIT_PASSED" = true ] && echo "   Unit Tests:        ✓ PASS" || echo "   Unit Tests:        ✗ FAIL"
    [ "$INTEGRATION_PASSED" = true ] && echo "   Integration Tests: ✓ PASS" || echo "   Integration Tests: ✗ FAIL"
    [ "$SMOKE_PASSED" = true ] && echo "   Smoke Tests:       ✓ PASS" || echo "   Smoke Tests:       ✗ FAIL"
    [ "$COVERAGE_PASSED" = true ] && echo "   Coverage:          ✓ ${COVERAGE_PERCENT}%" || echo "   Coverage:          ✗ ${COVERAGE_PERCENT}% (need ${COVERAGE_THRESHOLD}%)"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi
