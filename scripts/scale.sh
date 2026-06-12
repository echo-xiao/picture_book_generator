#!/bin/sh
# Switch Cloud Run resources between judging (full) and saver modes.
#
#   ./scripts/scale.sh full    # 4 vCPU / 8Gi — use 6/22 before judging starts
#   ./scripts/scale.sh saver   # 2 vCPU / 4Gi — use 7/06 after judging ends
#
# min-instances=1 and no-cpu-throttling are kept either way (needed so the
# background generation tasks aren't starved). Takes ~30s; verify health after.
set -e

REGION=us-central1
SERVICE=picture-book-gen

case "$1" in
  full)  CPU=4; MEM=8Gi; echo "→ FULL (judging): 4 vCPU / 8Gi" ;;
  saver) CPU=2; MEM=4Gi; echo "→ SAVER: 2 vCPU / 4Gi" ;;
  *) echo "Usage: $0 full|saver"; exit 1 ;;
esac

gcloud run services update "$SERVICE" --region "$REGION" --cpu "$CPU" --memory "$MEM"

echo ""
echo "Done. Verifying health:"
curl -s -o /dev/null -w "  /api/health -> HTTP %{http_code}\n" \
  "https://picture-book-gen-e3mtc46uua-uc.a.run.app/api/health"
