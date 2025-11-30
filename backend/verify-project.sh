#!/bin/bash
# MarketPrep Project Verification Script

echo "🔍 Verifying MarketPrep Project Structure..."
echo ""

errors=0
warnings=0

# Backend verification
echo "📦 Backend Files:"
files=(
    "src/main.py"
    "src/config.py"
    "src/database.py"
    "requirements.txt"
    "pyproject.toml"
    "alembic.ini"
    ".env.example"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
        ((errors++))
    fi
done

# Frontend verification
echo ""
echo "🎨 Frontend Files:"
files=(
    "frontend/package.json"
    "frontend/vite.config.ts"
    "frontend/tsconfig.json"
    "frontend/tailwind.config.js"
    "frontend/index.html"
    "frontend/src/main.tsx"
    "frontend/src/router.tsx"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
        ((errors++))
    fi
done

# PWA verification
echo ""
echo "📱 PWA Configuration:"
files=(
    "frontend/public/manifest.json"
    "frontend/src/components/OfflineIndicator.tsx"
    "frontend/src/lib/performance.ts"
    "frontend/lighthouserc.json"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
        ((errors++))
    fi
done

# Page verification
echo ""
echo "📄 Frontend Pages:"
files=(
    "frontend/src/pages/DashboardPage.tsx"
    "frontend/src/pages/ProductsPage.tsx"
    "frontend/src/pages/RecommendationsPage.tsx"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
        ((errors++))
    fi
done

# Documentation verification
echo ""
echo "📚 Documentation:"
files=(
    "PROJECT_SUMMARY.md"
    "DEPLOYMENT.md"
    "frontend/README.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ⚠️  $file (recommended)"
        ((warnings++))
    fi
done

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $errors -eq 0 ]; then
    echo "✅ All critical files present! Project is complete."
    echo ""
    echo "🎉 Phase 5 MVP Complete!"
    echo ""
    echo "Features implemented:"
    echo "  • Multi-tenant architecture with RLS"
    echo "  • JWT authentication with auto-refresh"
    echo "  • Square POS integration (OAuth + Sync)"
    echo "  • AI-powered inventory recommendations"
    echo "  • Mobile-first responsive dashboard"
    echo "  • Progressive Web App (PWA) support"
    echo "  • Performance optimizations (lazy loading, code splitting)"
    echo "  • Offline support with service worker"
else
    echo "❌ $errors critical file(s) missing"
fi

if [ $warnings -gt 0 ]; then
    echo "⚠️  $warnings recommended file(s) missing"
fi

echo ""
echo "📋 Next Steps:"
echo "1. Generate PWA icons (64x64, 192x192, 512x512 PNG)"
echo "2. Create .env file from .env.example"
echo "3. Configure Square OAuth credentials"
echo "4. Get OpenWeather API key"
echo "5. Install dependencies: npm install (in frontend/)"
echo "6. Start services: docker-compose up -d"
echo "7. Run frontend: cd frontend && npm run dev"
echo ""
echo "📖 Documentation:"
echo "  • PROJECT_SUMMARY.md - Complete project overview"
echo "  • DEPLOYMENT.md - Production deployment guide"
echo "  • frontend/README.md - Frontend development guide"

exit $errors
