terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
  required_version = ">= 0.13"

  backend "s3" {
    endpoints = {
      s3 = "https://storage.yandexcloud.net"
    }
    bucket   = "tf-states-bucket"
    region   = "ru-central1"
    key      = "ru-proxy/terraform.tfstate"

    skip_region_validation      = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
  }
}

provider "yandex" {
  token     = var.iam_token
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
  zone      = "ru-central1-a"
}

resource "yandex_compute_instance" "proxy_instance" {
  name        = "proxy"
  platform_id = "standard-v3"

  resources {
    cores         = 2
    memory        = 2
    core_fraction = 50
  }

  scheduling_policy {
    preemptible = var.preemptible
  }

  boot_disk {
    auto_delete = true
    initialize_params {
      image_id = "fd8snjpoq85qqv0mk9gi"  # Ubuntu 20.04
    }
  }

  network_interface {
    nat            = true
    nat_ip_address = ""
    subnet_id      = yandex_vpc_subnet.proxy_subnet.id
  }

  metadata = {
    user-data = file("metadata.yml")
  }
}

resource "yandex_vpc_network" "proxy_network" {
  name = "proxy-network"
}

resource "yandex_vpc_subnet" "proxy_subnet" {
  network_id     = yandex_vpc_network.proxy_network.id
  v4_cidr_blocks = ["10.5.0.0/28"]
}

output "instance_ip" {
  value = yandex_compute_instance.proxy_instance.network_interface[0].nat_ip_address
}
