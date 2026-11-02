# Privacy Policy

This policy covers the Olostep data source plugin for Dify.

## Data sent to Olostep

When you run a crawl, the plugin sends the start URL and your crawl options to the Olostep API at `https://api.olostep.com` over HTTPS. Your Olostep API key is sent in the `Authorization` header. Olostep uses these inputs to fetch the requested web pages and returns them to Dify.

Olostep's handling of this data is described in the [Olostep privacy policy](https://www.olostep.com/privacy-policy).

## Data stored by the plugin

The plugin does not collect, store or log your inputs, results or API key. It does not send data to any third party other than the Olostep API, and it includes no analytics or telemetry.

Dify stores your API key as a secret credential and stores crawled pages in your Knowledge Base according to your Dify workspace settings. This is handled by Dify, not by the plugin.

## Your responsibilities

Only crawl content you are allowed to access. To stop the plugin from using your account, remove the credential in Dify or revoke the key in the [Olostep dashboard](https://www.olostep.com/dashboard).

## Contact

info@olostep.com
