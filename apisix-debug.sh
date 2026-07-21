set -euo pipefail
OUT="apisix_support_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"

echo "== kubectl/cluster info ==" | tee "$OUT/00_cluster.txt"
{
  kubectl version --short || true
  kubectl config current-context || true
  echo
  echo "CRDs:"
  kubectl get crd | grep -i apisix || true
} >> "$OUT/00_cluster.txt" 2>&1

echo "== Namespaces: gateway, apps ==" | tee "$OUT/01_ns.txt"
{
  kubectl get all -n gateway -o wide || true
  echo
  kubectl get all -n apps -o wide || true
} >> "$OUT/01_ns.txt" 2>&1

echo "== Helm releases in gateway ==" | tee "$OUT/02_helm.txt"
{
  helm ls -n gateway || true
  echo
  echo "# Helm values for APISIX (if present)"
  helm get values apisix -n gateway || true
  echo
  echo "# Helm values for ingress-controller (chart name may differ; dumping all)"
  for r in $(helm ls -n gateway -o json | jq -r '.[].name'); do
    echo "---- values for $r ----"
    helm get values "$r" -n gateway || true
  done
} >> "$OUT/02_helm.txt" 2>&1

echo "== Ingress controller config/args ==" | tee "$OUT/03_ingress_controller.txt"
{
  kubectl -n gateway get deploy apisix-ingress-apisix-ingress-controller -o wide || true
  echo
  echo "# Container args:"
  kubectl -n gateway get deploy apisix-ingress-apisix-ingress-controller \
    -o jsonpath='{.spec.template.spec.containers[?(@.name=="manager")].args}' ; echo || true
} >> "$OUT/03_ingress_controller.txt" 2>&1

echo "== APISIX data plane svc/endpoints ==" | tee "$OUT/04_gateway_svc.txt"
{
  kubectl -n gateway get svc apisix-gateway -o yaml || true
  echo
  kubectl -n gateway get endpoints apisix-gateway -o yaml || true
} >> "$OUT/04_gateway_svc.txt" 2>&1

echo "== APISIX / Gateway custom resources ==" | tee "$OUT/05_custom_resources.txt"
{
  echo "# ApisixRoute (all namespaces)"
  kubectl get apisixroute -A -o yaml || true
  echo
  echo "# ApisixPluginConfig (all namespaces)"
  kubectl get apisixpluginconfig -A -o yaml || true
  echo
  echo "# GatewayProxy (if using Gateway mode)"
  kubectl get gatewayproxy -A -o yaml || true
  echo
  echo "# IngressClass"
  kubectl get ingressclass -o yaml || true
  echo
  echo "# Gateway API objects (if any)"
  kubectl get gateway -A -o yaml || true
  kubectl get httproute -A -o yaml || true
} >> "$OUT/05_custom_resources.txt" 2>&1

echo "== Logs ==" | tee "$OUT/06_logs.txt"
{
  echo "---- APISIX ingress-controller (manager & adc-server) ----"
  kubectl -n gateway logs deploy/apisix-ingress-apisix-ingress-controller --all-containers --tail=1500 || true
  echo
  echo "---- APISIX data plane ----"
  kubectl -n gateway logs deploy/apisix --tail=1000 || true
} >> "$OUT/06_logs.txt" 2>&1

echo "== Admin API quick check (routes, plugin_configs) ==" | tee "$OUT/07_admin_checks.txt"
{
  # Try cluster-internal first using a throwaway curl pod with jq
  kubectl -n gateway run curlbox-$$ --rm -i --restart=Never --image=ghcr.io/stedolan/jq:latest -q -- \
    sh -lc 'apk add --no-cache curl >/dev/null 2>&1 || true; \
      curl -s -H "X-API-KEY: ${APISIX_ADMIN_KEY:-edd1c9f034335f136f87ad84b625c8f1}" \
        http://apisix-admin.gateway.svc.cluster.local:9180/apisix/admin/routes | jq . ; \
      curl -s -H "X-API-KEY: ${APISIX_ADMIN_KEY:-edd1c9f034335f136f87ad84b625c8f1}" \
        http://apisix-admin.gateway.svc.cluster.local:9180/apisix/admin/plugin_configs | jq .' \
    || true
} >> "$OUT/07_admin_checks.txt" 2>&1

tar -czf "$OUT.tgz" "$OUT"
echo "Created $OUT.tgz"
