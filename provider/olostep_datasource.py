from collections.abc import Mapping
from typing import Any

from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.interfaces.datasource import DatasourceProvider

from olostep_client.client import OlostepClient, OlostepError


class OlostepDatasourceProvider(DatasourceProvider):
    def _validate_credentials(self, credentials: Mapping[str, Any]) -> None:
        try:
            OlostepClient(credentials.get("api_key")).check_key()
        except OlostepError as error:
            raise ToolProviderCredentialValidationError(str(error)) from None
