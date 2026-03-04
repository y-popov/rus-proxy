from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode, quote
from yandex.cloud.compute.v1.instance_pb2 import Instance
from yandexcloud import SDK

from src.template import load_template
from src.vm import delete_proxy_vm, create_proxy_vm
from src.keys import generate_keypair, generate_short_id, generate_uuid


@dataclass
class LaunchResult:
    ip: str
    client_link: str


class Service:
    def __init__(self, sdk: SDK, folder_id: str, metadata_template: Path):
        self.sdk = sdk
        self.folder_id = folder_id
        self.metadata_template = load_template(metadata_template)

    @staticmethod
    def get_instance_public_ip(instance: Instance) -> str:
        return instance.network_interfaces[0].primary_v4_address.one_to_one_nat.address

    @staticmethod
    def generate_v2ray_link(uuid: str, server_ip: str, public_key: str, short_id: str) -> str:
        params = {
            "encryption": "none",
            "flow": "xtls-rprx-vision",
            "security": "reality",
            "sni": "www.cloudflare.com",
            "fp": "chrome",
            "pbk": public_key,
            "sid": short_id,
            "type": "tcp"
        }

        query_string = urlencode(params)
        server_name = "RU-Server"

        return f"vless://{uuid}@{server_ip}:443?{query_string}#{quote(server_name)}"

    def launch(self) -> LaunchResult:
        keypair = generate_keypair(urlsafe=True)
        client_id = generate_uuid()
        short_id = generate_short_id()

        metadata = self.metadata_template.render(
            client_uuid=client_id,
            reality_private_key=keypair.private_key,
            short_id=short_id
        )

        instance = create_proxy_vm(
            sdk=self.sdk,
            folder_id=self.folder_id,
            cloud_config=metadata
        )

        ip = self.get_instance_public_ip(instance)

        client_link = self.generate_v2ray_link(
            uuid=client_id,
            server_ip=ip,
            public_key=keypair.public_key,
            short_id=short_id
        )

        return LaunchResult(ip=ip, client_link=client_link)

    def stop(self) -> None:
        delete_proxy_vm(sdk=self.sdk, folder_id=self.folder_id)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    svc = Service(
        sdk=SDK(token=os.getenv("YC_OAUTH_TOKEN")),
        folder_id=os.getenv("YC_FOLDER_ID"),
        metadata_template=Path("../templates/metadata-vpn.yml.j2")
    )

    svc.launch()
    svc.stop()
