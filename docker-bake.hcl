variable "COMPOSE_PROJECT_NAME" {
  default = "app"
}

variable "LLM" {
  default = "false"
}

variable "TAG" {
  default = "latest"
}

group "default" {
  targets = ["backend"]
}

target "backend" {
  context = "backend"
  args = { LLM = LLM }
  tags = ["${COMPOSE_PROJECT_NAME}-backend:${TAG}"]
  output = ["type=docker"]
}
