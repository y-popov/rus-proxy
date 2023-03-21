## Installation

## Configuration
### Authentication
First нужно получить OAuth-токен по [ссылке](https://oauth.yandex.ru/authorize?response_type=token&client_id=1a6990aa636648e9b2ef855fa7bec2fb).

Then exchange it on IAM-token: 
```bash
curl -d "{\"yandexPassportOauthToken\":\"<OAuth-token>\"}" "https://iam.api.cloud.yandex.net/iam/v1/tokens"
```

Полученное значение `iamToken` подставить в `tfvars`-файл

https://cloud.yandex.ru/docs/tutorials/infrastructure-management/terraform-quickstart#get-credentials

## Usage

### Spin up proxy instance
```bash
.\terraform.exe apply -var-file="my.tfvars"
```

### Remove proxy instance
```bash
.\terraform.exe destroy -var-file="my.tfvars"
```