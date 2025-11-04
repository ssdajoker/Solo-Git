#!/bin/bash
echo "🔍 Running static analysis..."

echo ""
echo "1️⃣ Type checking (mypy)..."
mypy sologit --strict --show-error-codes --pretty 2>&1 || {
    echo "⚠️  Type checking found issues (continuing...)"
}

echo ""
echo "2️⃣ Linting (ruff)..."
ruff check sologit tests --show-source 2>&1 || {
    echo "⚠️  Linting found issues (continuing...)"
}

echo ""
echo "3️⃣ Security scan (bandit)..."
bandit -r sologit -f screen -ll 2>&1 || {
    echo "⚠️  Security scan found issues (continuing...)"
}

echo ""
echo "4️⃣ Dead code detection (vulture)..."
vulture sologit --min-confidence 80 2>&1 || {
    echo "⚠️  Dead code detected (continuing...)"
}

echo ""
echo "✅ Static analysis complete!"
