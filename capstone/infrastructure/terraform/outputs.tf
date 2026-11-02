output "namespace" {
  description = "Namespace hosting the customer support service"
  value       = kubernetes_namespace.support.metadata[0].name
}

output "release_name" {
  description = "Helm release name"
  value       = helm_release.customer_support.name
}

output "service_endpoint" {
  description = "In-cluster service endpoint"
  value       = "http://customer-support.${var.namespace}.svc.cluster.local:8000"
}