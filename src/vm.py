import os
import logging

from typing import Optional
from pathlib import Path
from yandexcloud import SDK

from yandex.cloud.vpc.v1.network_pb2 import Network
from yandex.cloud.vpc.v1.network_service_pb2 import ListNetworksRequest
from yandex.cloud.vpc.v1.network_service_pb2_grpc import NetworkServiceStub

from yandex.cloud.compute.v1.zone_pb2 import Zone
from yandex.cloud.compute.v1.zone_service_pb2 import ListZonesRequest
from yandex.cloud.compute.v1.zone_service_pb2_grpc import ZoneServiceStub

from yandex.cloud.operation.operation_pb2 import Operation
from yandex.cloud.compute.v1.instance_pb2 import IPV4, SchedulingPolicy, Instance
from yandex.cloud.compute.v1.instance_service_pb2_grpc import InstanceServiceStub
from yandex.cloud.compute.v1.instance_service_pb2 import (
    AttachedDiskSpec,
    CreateInstanceMetadata,
    CreateInstanceRequest,
    DeleteInstanceRequest,
    ListInstancesRequest,
    NetworkInterfaceSpec,
    OneToOneNatSpec,
    PrimaryAddressSpec,
    ResourcesSpec,
)

PROXY_INSTANCE_NAME = "proxy"
PROXY_NETWORK_NAME = "proxy-network"

def get_available_zone(sdk: SDK) -> Zone:
    zone_service = sdk.client(ZoneServiceStub)

    zones = zone_service.List(ListZonesRequest()).zones
    for z in zones:
        if z.status == Zone.Status.UP:
            return z

    raise RuntimeError("No zones available")

def get_network(sdk: SDK, folder_id: str, network_name: str) -> Network:
    network_service = sdk.client(NetworkServiceStub)

    networks = network_service.List(
        ListNetworksRequest(
            folder_id=folder_id,
            filter=f"name = '{PROXY_NETWORK_NAME}'"
        )
    ).networks

    if len(networks) == 0:
        raise RuntimeError(f"Network {network_name} not found")

    return networks[0]

def create_proxy_vm(sdk: SDK, folder_id: str, script: Path, preemptible=True) -> Instance:
    zone = get_available_zone(sdk)
    network = get_network(sdk, folder_id, PROXY_NETWORK_NAME)
    subnet_id = sdk.helpers.find_subnet_id(folder_id=folder_id, zone_id=zone.id, network_id=network.id)

    instance_service = sdk.client(InstanceServiceStub)

    metadata = {}
    if script is not None:
        metadata["user-data"] = script.read_text()

    op: Operation = instance_service.Create(
        CreateInstanceRequest(
            folder_id=folder_id,
            zone_id=zone.id,
            name=PROXY_INSTANCE_NAME,
            platform_id="standard-v3",
            resources_spec=ResourcesSpec(
                memory=2 * 2 ** 30,
                cores=2,
                core_fraction=50
            ),
            scheduling_policy=SchedulingPolicy(
                preemptible=preemptible
            ),
            boot_disk_spec=AttachedDiskSpec(
                auto_delete=True,
                disk_spec=AttachedDiskSpec.DiskSpec(
                    type_id="network-hdd",
                    size=20 * 2 ** 30,
                    image_id="fd8snjpoq85qqv0mk9gi"
                ),
            ),
            network_interface_specs=[
                NetworkInterfaceSpec(
                    subnet_id=subnet_id,
                    primary_v4_address_spec=PrimaryAddressSpec(
                        one_to_one_nat_spec=OneToOneNatSpec(
                            ip_version=IPV4,
                        )
                    )
                )
            ],
            metadata=metadata,
        )
    )

    logging.info("Creating initiated")

    operation_result = sdk.wait_operation_and_get_result(
        operation=op,
        response_type=Instance,
        meta_type=CreateInstanceMetadata,
    )

    logging.info(f"VM created. {operation_result.meta}")

    return operation_result.response


def delete_proxy_vm(sdk: SDK, folder_id: str):
    instance_service = sdk.client(InstanceServiceStub)

    instances = instance_service.List(
        ListInstancesRequest(
            folder_id=folder_id,
            filter=f"name = '{PROXY_INSTANCE_NAME}'"
        )
    ).instances

    if len(instances) == 0:
        logging.warning("No proxy instance found")
        return None

    instance_id = instances[0].id

    op: Operation = instance_service.Delete(
        DeleteInstanceRequest(instance_id=instance_id)
    )

    logging.info("Deleting initiated")

    return sdk.wait_operation_and_get_result(operation=op)


def get_disk_types(sdk: SDK):
    from yandex.cloud.compute.v1.disk_type_service_pb2 import ListDiskTypesRequest, ListDiskTypesResponse
    from yandex.cloud.compute.v1.disk_type_service_pb2_grpc import DiskTypeServiceStub

    disk_service = sdk.client(DiskTypeServiceStub)
    resp: ListDiskTypesResponse = disk_service.List(ListDiskTypesRequest())
    return resp.disk_types


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(level=logging.INFO)

    folder = os.getenv("YC_FOLDER_ID")
    script = Path("../terraform/metadata.yml")

    sdk = SDK(token=os.getenv("YC_OAUTH_TOKEN"))

    proxy = create_proxy_vm(sdk, folder_id=folder, script=script)

    ip = proxy.network_interfaces[0].primary_v4_address.one_to_one_nat.address
    logging.info(f"IP address: {ip}")

    delete_proxy_vm(sdk, folder_id=folder)
