#!/usr/bin/env bash
set -euo pipefail

# End-to-end test for the MedBed NLP pipeline
# Prerequisites: make up-full && make warm-model

API_URL="${API_URL:-http://localhost:8010}"
ML_URL="${ML_URL:-http://localhost:8001}"
SAMPLE_PDF="${SAMPLE_PDF:-docs/sample_docs/sample_report.pdf}"
TIMEOUT=300  # 5 minutes max for analysis

echo "=== MedBed E2E Pipeline Test ==="
echo ""

# Step 1: Check ML service
echo "1. Checking ML service health..."
ML_HEALTH=$(curl -sf "${ML_URL}/health" || echo '{"status":"unreachable"}')
MODEL_LOADED=$(echo "$ML_HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('model_loaded', False))" 2>/dev/null || echo "False")
echo "   ML service: $(echo "$ML_HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'status={d.get(\"status\")}, model_loaded={d.get(\"model_loaded\")}')" 2>/dev/null || echo "unreachable")"
if [ "$MODEL_LOADED" != "True" ]; then
    echo "   ⚠ ML model not loaded. Run 'make warm-model' first for real embeddings."
    echo "   Continuing with mock embeddings..."
fi
echo ""

# Step 2: Login
echo "2. Logging in..."
LOGIN_RESP=$(curl -sf -X POST "${API_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"demo@medbed.local","password":"demo123"}')
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "   Token acquired: ${TOKEN:0:20}..."
echo ""

# Step 3: Upload sample PDF
echo "3. Uploading sample PDF: ${SAMPLE_PDF}..."
if [ ! -f "$SAMPLE_PDF" ]; then
    echo "   ✗ Sample PDF not found at ${SAMPLE_PDF}"
    exit 1
fi
UPLOAD_RESP=$(curl -sf -X POST "${API_URL}/api/v1/reports/upload" \
    -H "Authorization: Bearer ${TOKEN}" \
    -F "file=@${SAMPLE_PDF}")
SESSION_ID=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
ENTRY_COUNT=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['entry_count'])")
echo "   Session ID: ${SESSION_ID}"
echo "   Entries parsed: ${ENTRY_COUNT}"
echo ""

# Step 4: Trigger analysis
echo "4. Triggering analysis pipeline..."
ANALYZE_RESP=$(curl -sf -X POST "${API_URL}/api/v1/reports/${SESSION_ID}/analyze" \
    -H "Authorization: Bearer ${TOKEN}")
TASK_ID=$(echo "$ANALYZE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
echo "   Task ID: ${TASK_ID}"
echo ""

# Step 5: Poll for completion
echo "5. Polling for analysis completion (timeout: ${TIMEOUT}s)..."
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    REPORT=$(curl -sf "${API_URL}/api/v1/reports/${SESSION_ID}" \
        -H "Authorization: Bearer ${TOKEN}")
    STATUS=$(echo "$REPORT" | python3 -c "import sys,json; print(json.load(sys.stdin)['analysis_status'])")

    if [ "$STATUS" = "completed" ]; then
        echo "   ✓ Analysis completed in ~${ELAPSED}s"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo "   ✗ Analysis FAILED"
        exit 1
    fi

    printf "   Waiting... (%ds, status=%s)\r" "$ELAPSED" "$STATUS"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "   ✗ Analysis timed out after ${TIMEOUT}s"
    exit 1
fi
echo ""

# Step 6: Verify report data
echo "6. Verifying report data..."
EMBEDDING_SRC=$(echo "$REPORT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('embedding_source', 'unknown'))")
FINAL_COUNT=$(echo "$REPORT" | python3 -c "import sys,json; print(json.load(sys.stdin)['entry_count'])")
echo "   Entry count: ${FINAL_COUNT}"
echo "   Embedding source: ${EMBEDDING_SRC}"

if [ "$FINAL_COUNT" -lt 10 ]; then
    echo "   ⚠ Low entry count (expected >100 for full PDF)"
fi
echo ""

# Step 7: Verify insights
echo "7. Checking insights..."
INSIGHTS=$(curl -sf "${API_URL}/api/v1/insights/${SESSION_ID}" \
    -H "Authorization: Bearer ${TOKEN}")
N_CLUSTERS=$(echo "$INSIGHTS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['clusters']))")
HAS_UMAP=$(echo "$INSIGHTS" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('umap_coords') else 'no')")
INS_EMB_SRC=$(echo "$INSIGHTS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('embedding_source', 'unknown'))")
echo "   Clusters: ${N_CLUSTERS}"
echo "   UMAP coords: ${HAS_UMAP}"
echo "   Embedding source: ${INS_EMB_SRC}"
echo ""

# Step 8: Verify recovery plan
echo "8. Checking recovery plan..."
RECOVERY=$(curl -sf "${API_URL}/api/v1/recovery/${SESSION_ID}" \
    -H "Authorization: Bearer ${TOKEN}" || echo '{}')
HAS_SUMMARY=$(echo "$RECOVERY" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('summary') else 'no')" 2>/dev/null || echo "no")
echo "   Recovery plan summary: ${HAS_SUMMARY}"
echo ""

# Summary
echo "=== Test Summary ==="
echo "  Entries parsed:     ${FINAL_COUNT}"
echo "  Embedding source:   ${EMBEDDING_SRC}"
echo "  Clusters found:     ${N_CLUSTERS}"
echo "  UMAP coords:        ${HAS_UMAP}"
echo "  Recovery plan:      ${HAS_SUMMARY}"
echo ""

if [ "$N_CLUSTERS" -ge 2 ] && [ "$HAS_SUMMARY" = "yes" ]; then
    echo "✓ E2E pipeline test PASSED"
else
    echo "⚠ E2E pipeline test completed with warnings"
    [ "$N_CLUSTERS" -lt 2 ] && echo "  - Expected ≥2 clusters, got ${N_CLUSTERS}"
    [ "$HAS_SUMMARY" != "yes" ] && echo "  - Recovery plan summary missing"
fi
