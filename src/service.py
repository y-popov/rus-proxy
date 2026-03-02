from dataclasses import dataclass
from pathlib import Path
from yandex.cloud.compute.v1.instance_pb2 import Instance
from yandexcloud import SDK

from src.template import load_template
from src.vm import delete_proxy_vm, create_proxy_vm
from src.vpn import generate_wg_keypair


@dataclass
class LaunchResult:
    ip: str
    client_config: str


class Service:
    def __init__(self, sdk: SDK, folder_id: str, metadata_template: Path, client_config_template: Path):
        self.sdk = sdk
        self.folder_id = folder_id
        self.metadata_template = load_template(metadata_template)
        self.client_config_template = load_template(client_config_template)

    @staticmethod
    def get_instance_public_ip(instance: Instance) -> str:
        return instance.network_interfaces[0].primary_v4_address.one_to_one_nat.address

    def launch(self) -> LaunchResult:
        server_keypair = generate_wg_keypair()
        client_keypair = generate_wg_keypair()

        metadata = self.metadata_template.render(
            server_private_key=server_keypair.private_key,
            client_public_key=client_keypair.public_key,
        )

        instance = create_proxy_vm(
            sdk=self.sdk,
            folder_id=self.folder_id,
            cloud_config=metadata
        )

        ip = self.get_instance_public_ip(instance)

        client_config = self.client_config_template.render(
            client_private_key=client_keypair.private_key,
            server_public_key=server_keypair.public_key,
            instance_ip=ip
        )

        return LaunchResult(ip=ip, client_config=client_config)

    def stop(self) -> None:
        delete_proxy_vm(sdk=self.sdk, folder_id=self.folder_id)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    svc = Service(
        sdk=SDK(token=os.getenv("YC_OAUTH_TOKEN")),
        folder_id=os.getenv("YC_FOLDER_ID"),
        metadata_template=Path("../templates/metadata-vpn.yml.j2"),
        client_config_template=Path("../templates/client_config.yml.j2")
    )

    svc.launch()
    svc.stop()
