variable "COMPOSE_PROJECT_NAME" {
  default = "app"
}

variable "TAG" {
  default = "latest"
}

group "default" {
  targets = ["backend"]
}

target "backend" {
  context = "backend"
  tags = ["${COMPOSE_PROJECT_NAME}-backend:${TAG}"]
  output = ["type=docker"]
}
