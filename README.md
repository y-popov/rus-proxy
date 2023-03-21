# Simple Russian Proxy
## Introduction
In 2022 a lot of russian web-services, government particularly, hided themselves behind a firewall restricting access
from outside of Russia. This disgraceful decision broke habits of russians living abroad disabling them using essential
services. This repo aims to ease the suffering.

The repo contains the code for spinning up a very basic http proxy server in Yandex Cloud in just one command allowing
to access desired websites.   
A typical pattern for using this proxy consists of 
1) creating the server
2) using the server
3) killing the server

This allows to keep spendings for just ₽2 per hour.


## Installation
Download repo
```bash
git clone --depth 1 https://github.com/y-popov/rus-proxy.git
```

Download [Terraform](https://developer.hashicorp.com/terraform/downloads)

## Configuration

### Create a Yandex Cloud account
Cloud is [here](https://console.cloud.yandex.ru).

### Dump cloud details
Go to the [page](https://console.cloud.yandex.ru/cloud/).
Copy your cloud-ID and folder-ID.

If you struggle here are help pages: 
[[1-cloud]](https://cloud.yandex.com/en/docs/resource-manager/operations/cloud/get-id)
[[2-folder]](https://cloud.yandex.com/en/docs/resource-manager/operations/folder/get-id)

Paste cloud details into your `tfvars`-file. Template is in the repo.

### Authentication
At first, we need your Yandex OAuth-token. Copy it from [here](https://oauth.yandex.ru/authorize?response_type=token&client_id=1a6990aa636648e9b2ef855fa7bec2fb).

Then exchange it on IAM-token: 
```bash
curl -d "{\"yandexPassportOauthToken\":\"<OAuth-token>\"}" "https://iam.api.cloud.yandex.net/iam/v1/tokens"
```

Copy `iamToken` value and paste it into `tfvars`-file.

### Initialisation
Just type
```bash
terraform init 
```

## Usage

### Spin up proxy instance
As easy as
```bash
terraform apply -auto-approve -var-file="my.tfvars"
```

### Fill-in proxy details
The previous step will report you IP address of your very own proxy server.
Use it along with port 3128. No credentials required.

### Remove proxy instance
In the end of your session kill the server:
```bash
terraform destroy -var-file="my.tfvars"
```
Type `yes` when prompted.
