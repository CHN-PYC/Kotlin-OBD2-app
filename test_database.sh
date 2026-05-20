#!/bin/bash

# Database CRUD Test Script
# 测试 Room 数据库的增删改查功能

echo "========================================"
echo "  OBD2 Database CRUD Test"
echo "========================================"
echo ""

# 检查 Gradle
if ! command -v ./gradlew &> /dev/null; then
    echo "❌ Gradle wrapper not found!"
    exit 1
fi

echo "✓ Gradle wrapper found"
echo ""

# 运行单元测试
echo "Running database tests..."
echo "----------------------------------------"

./gradlew testDebugUnitTest --tests "*DatabaseCrudTest*" --no-daemon

# 检查结果
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "  ✅ All database tests passed!"
    echo "========================================"
    echo ""
    echo "Test coverage:"
    echo "  ✓ CREATE - Insert single/multiple records"
    echo "  ✓ READ - Get all history, time range query"
    echo "  ✓ UPDATE - Record modification"
    echo "  ✓ DELETE - Delete all, delete old records"
    echo "  ✓ Extended PIDs - All 21 parameters storage"
    echo "  ✓ Boundary tests - Min/Max values"
    echo "  ✓ Concurrent inserts - Multi-threading"
    echo "  ✓ Performance - Bulk insert & query"
    echo ""
else
    echo ""
    echo "========================================"
    echo "  ❌ Some tests failed!"
    echo "========================================"
    echo ""
    echo "Check test report for details:"
    echo "  app/build/reports/tests/testDebugUnitTest/index.html"
    echo ""
    exit 1
fi
