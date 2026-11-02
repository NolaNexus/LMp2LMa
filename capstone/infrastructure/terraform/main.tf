terraform {
  required_version = ">= 1.5.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
}

provider "helm" {
  kubernetes {
    config_path = var.kubeconfig_path
  }
}

resource "kubernetes_namespace" "support" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/part-of" = "ml-architect-capstone"
    }
  }
}

resource "helm_release" "customer_support" {
  name       = "customer-support"
  chart      = "${path.module}/helm/customer-support"
  namespace  = kubernetes_namespace.support.metadata[0].name
  timeout    = 300
  wait       = true

  values = [
    yamlencode({
      image = {
        repository = var.image_repository
        tag        = var.image_tag
      }
      env = {
        LLM_PROVIDER = var.llm_provider
      }
      replicaCount = var.replica_count
    })
  ]
}