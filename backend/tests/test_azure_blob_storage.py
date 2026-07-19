from types import SimpleNamespace

from app.services import storage_service


def test_azure_blob_storage_uses_managed_identity_account_url(monkeypatch):
    captured: dict[str, str] = {}

    class FakeServiceClient:
        def get_container_client(self, container: str):
            captured["container"] = container
            return object()

    def fake_managed_identity_client(account_url: str):
        captured["account_url"] = account_url
        return FakeServiceClient()

    monkeypatch.setattr(storage_service, "_managed_identity_blob_service_client", fake_managed_identity_client)
    monkeypatch.setattr(
        storage_service,
        "get_settings",
        lambda: SimpleNamespace(
            azure_storage_account_url="https://unit-test.blob.core.windows.net",
            azure_storage_connection_string="",
            azure_storage_container="uploads",
            deployment_environment="production",
        ),
    )

    storage_service.AzureBlobStorage()

    assert captured == {
        "account_url": "https://unit-test.blob.core.windows.net",
        "container": "uploads",
    }
