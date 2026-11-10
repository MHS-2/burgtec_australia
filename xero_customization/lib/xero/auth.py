from requests_oauthlib import OAuth1, OAuth2, OAuth2Session
from odoo.addons.sync_xero_connector.lib.xero.auth import OAuth2Credentials

from odoo.addons.sync_xero_connector.lib.xero.constants import (
    ACCESS_TOKEN_URL,
    AUTHORIZE_URL,
    REQUEST_TOKEN_URL,
    XERO_BASE_URL,
    XERO_OAUTH2_AUTHORIZE_URL,
    XERO_OAUTH2_CONNECTIONS_URL,
    XERO_OAUTH2_TOKEN_URL,
    XeroScopes,
)

from odoo.addons.sync_xero_connector.lib.xero.exceptions import (
    XeroAccessDenied,
    XeroBadRequest,
    XeroException,
    XeroExceptionUnknown,
    XeroForbidden,
    XeroInternalError,
    XeroNotAvailable,
    XeroNotFound,
    XeroNotImplemented,
    XeroNotVerified,
    XeroRateLimitExceeded,
    XeroUnauthorized,
)

class CustomOAuth2Credentials(OAuth2Credentials):

    def __init__(
        self,
        client_id,
        client_secret,
        second_client_id=None,
        second_client_secret=None,
        second_callback_uri=None,
        **kwargs
    ):
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            **kwargs
        )

        self.second_client_id = second_client_id
        self.second_client_secret = second_client_secret
        self.second_callback_uri = second_callback_uri

    def generate_second_url(self):
        """Generate an authorization URL for the second Xero app."""

        session = OAuth2Session(
            self.second_client_id,
            scope=self.scope,
            redirect_uri=self.second_callback_uri,
        )

        url, self.auth_state = session.authorization_url(
            XERO_OAUTH2_AUTHORIZE_URL,
            state=self.auth_state,
        )

        return url
    
    def second_verify(self, auth_secret):
        """Verify and return OAuth2 token."""
        import os
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        session = OAuth2Session(
            self.second_client_id,
            state=self.auth_state,
            scope=self.scope,
            redirect_uri=self.second_callback_uri,
        )
        try:
            token = session.fetch_token(
                XERO_OAUTH2_TOKEN_URL,
                client_secret=self.second_client_secret,
                authorization_response=auth_secret,
                headers=self.headers,
            )
        # Various different exceptions may be raised, so pass the exception
        # through as XeroAccessDenied
        except Exception as e:
            raise XeroAccessDenied(e)
        self._init_oauth(token)