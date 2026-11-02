variable "kubeconfig_path" {
  description = "Path to the kubeconfig used for deployment"
  type        = string
  default     = "~/.kube/config"
}

variable "namespace" {
  description = "Kubernetes namespace for the support service"
  type        = string
  default     = "customer-support"
}

variable "image_repository" {
  description = "Container image repository"
  type        = string
  default     = "ghcr.io/example/customer-support"
}

variable "image_tag" {
  description = "Container image tag"
  type        = string
  default     = "1.0.0"
}

variable "llm_provider" {
  description = "LLM provider used by the service (mock, openai, anthropic, local)"
  type        = string
  default     = "mock"

  validation {
    condition     = contains(["mock", "openai", "anthropic", "local"], var.llm_provider)
    error_message = "llm_provider must be one of: mock, openai, anthropic, local."
  }
}

variable "replica_count" {
  description = "Initial replica count"
  type        = number
  default     = 2
}