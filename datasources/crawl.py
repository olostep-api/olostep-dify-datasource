from collections.abc import Generator, Mapping
from typing import Any

from dify_plugin.entities.datasource import WebsiteCrawlMessage, WebSiteInfo, WebSiteInfoDetail
from dify_plugin.interfaces.datasource.website import WebsiteCrawlDatasource

from olostep_client.client import OlostepClient, OlostepError, title_and_description

DEFAULT_PAGES = 10
MAX_PAGES = 100_000


def split_patterns(value: Any) -> list[str]:
    return [pattern.strip() for pattern in str(value or "").split(",") if pattern.strip()]


def crawl_options(parameters: Mapping[str, Any]) -> dict[str, Any]:
    """Turns the Dify form into Olostep crawl options."""
    subpages = parameters.get("crawl_subpages", True)
    try:
        limit = int(parameters.get("limit") or DEFAULT_PAGES)
    except (TypeError, ValueError):
        limit = DEFAULT_PAGES
    options: dict[str, Any] = {"max_pages": max(1, min(limit, MAX_PAGES)) if subpages else 1}
    if not subpages:
        return options
    if parameters.get("max_depth") not in (None, ""):
        options["max_depth"] = int(parameters["max_depth"])
    if include := split_patterns(parameters.get("include_paths")):
        options["include_urls"] = include
    if exclude := split_patterns(parameters.get("exclude_paths")):
        options["exclude_urls"] = exclude
    return options


class CrawlDatasource(WebsiteCrawlDatasource):
    def _get_website_crawl(
        self, datasource_parameters: Mapping[str, Any]
    ) -> Generator[WebsiteCrawlMessage, None, None]:
        try:
            client = OlostepClient(self.runtime.credentials.get("api_key"))
            yield from crawl_messages(self, client, datasource_parameters)
        except OlostepError as error:
            raise ValueError(str(error)) from None


def crawl_messages(
    datasource: WebsiteCrawlDatasource, client: OlostepClient, parameters: Mapping[str, Any]
) -> Generator[WebsiteCrawlMessage, None, None]:
    options = crawl_options(parameters)
    total = options["max_pages"]
    crawl_id = client.start_crawl(parameters.get("url"), options)

    progress = WebSiteInfo(status="processing", web_info_list=[], total=total, completed=0)
    yield datasource.create_crawl_message(progress)

    for info in client.wait_for_crawl(crawl_id):
        progress.completed = int(info.get("pages_count") or 0)
        yield datasource.create_crawl_message(progress)

    pages: list[WebSiteInfoDetail] = []
    for batch in client.crawl_pages(crawl_id):
        for page in batch:
            title, description = title_and_description(page["markdown"], page["url"])
            pages.append(
                WebSiteInfoDetail(
                    source_url=page["url"], content=page["markdown"], title=title, description=description
                )
            )
        progress.completed = len(pages)
        yield datasource.create_crawl_message(progress)

    done = WebSiteInfo(status="completed", web_info_list=pages, total=len(pages), completed=len(pages))
    yield datasource.create_crawl_message(done)
