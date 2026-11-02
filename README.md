# Olostep

Olostep is web data infrastructure for AI agents and enterprise AI workflows. Its APIs provide live web search, scraping and crawling to extract, clean and structure data from the web.

This data source plugin crawls any website into your Dify Knowledge Base as clean, LLM-ready markdown. To use Olostep in agents and workflows, install the [Olostep tool plugin](https://marketplace.dify.ai/plugin/olostep/olostep).

Source repository: https://github.com/olostep-api/olostep-dify-datasource

## Why Olostep

- Web data infrastructure for developers and enterprises
- Scales to hundreds of millions to billions of requests per customer per month
- The most performant, reliable and cost-effective API on the market
- Used by the fastest-growing AI companies

From extracting data from a handful of URLs to crawling hundreds of millions of pages, Olostep gives developers and AI companies reliable, scalable and highly cost-effective access to clean, structured web data.

## Requirements

- Dify 1.9.0 or later
- An Olostep API key

## Setup

1. Sign up at [olostep.com](https://www.olostep.com) and copy your API key from the [Olostep dashboard](https://www.olostep.com/dashboard).
2. In Dify, go to **Plugins**, find **Olostep** under Data Source in the Marketplace and click **Install**.
3. In your Knowledge Pipeline, add Olostep as the data source, then add your API key when asked.

## Usage

Enter a start URL and choose your options:

| Option | What it does |
|---|---|
| Start URL | The page to start crawling from |
| Crawl subpages | Follow links from the start URL, or read only that page |
| Maximum pages | The maximum number of pages to crawl (1 to 100k) |
| Maximum depth | How many links deep to follow |
| URL patterns to include | Comma-separated glob patterns, for example `/docs/**` |
| URL patterns to exclude | Comma-separated glob patterns, for example `/careers/**` |

Each page is returned with its URL, markdown content, title and description, ready for chunking in your Knowledge Pipeline.

## Connection requirements

The plugin connects only to the Olostep API at `https://api.olostep.com` over HTTPS. Your Dify instance needs outbound network access to that host. Rate limits and server errors are retried automatically.

## Credentials

The plugin needs an Olostep API key. It is stored by Dify as a secret and sent to the Olostep API in the `Authorization` header.

## Support

- Website: https://www.olostep.com
- Documentation: https://docs.olostep.com
- Email: info@olostep.com
- Privacy: see [PRIVACY.md](PRIVACY.md) and https://www.olostep.com/privacy-policy
