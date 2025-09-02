variable "cloud_id" {
  type     = string
  nullable = false
}

variable "folder_id" {
  type     = string
  nullable = false
}

variable "iam_token" {
  type     = string
  nullable = false
}

variable "preemptible" {
  type        = bool
  default     = false
  description = "reduces the price twice but instance may stop suddenly"
}
