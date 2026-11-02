import json

import httpx
import pytest
from dify_plugin.entities.datasource import WebSiteInfo

from datasources.crawl import crawl_messages, crawl_options, split_patterns
from olostep_client.client import OlostepClient, OlostepError, title_and_description


class FakeDatasource:
    def create_crawl_message(self, info: WebSiteInfo) -> WebSiteInfo:
        return info.model_copy(deep=True)


def make_client(handler):
    return OlostepClient("test-key", transport=httpx.MockTransport(handler), sleep=lambda _: None)


def crawl_api(pages, statuses=("in_progress", "completed"), page_size=None):
    states = iter(statuses)
    sent = {}

    def handler(request):
        path = request.url.path
        if path == "/v1/crawls" and request.method == "POST":
            sent.update(json.loads(request.content))
            return httpx.Response(200, json={"id": "crawl_1", "status": "in_progress"})
        if path == "/v1/crawls/crawl_1":
            return httpx.Response(200, json={"status": next(states), "pages_count": len(pages)})
        if path == "/v1/crawls/crawl_1/pages":
            start = int(request.url.params.get("cursor", 0))
            size = page_size or int(request.url.params["limit"])
            found = pages[start:start + size]
            body = {"pages": found}
            if found:
                body["cursor"] = start + size
            return httpx.Response(200, json=body)
        if path == "/v1/retrieve":
            return httpx.Response(200, json={"markdown_content": f"# {request.url.params['retrieve_id']}\n\nBody text"})
        raise AssertionError(f"unexpected request {request.method} {path}")

    return handler, sent


def pages(count):
    return [{"url": f"https://a.com/{i}", "retrieve_id": f"r{i}"} for i in range(count)]


def run(handler, parameters=None):
    params = {"url": "https://a.com", **(parameters or {})}
    return list(crawl_messages(FakeDatasource(), make_client(handler), params))


def test_crawl_ends_with_every_page_and_required_fields():
    handler, sent = crawl_api(pages(3))
    messages = run(handler, {"limit": 3})

    assert sent == {"start_url": "https://a.com", "max_pages": 3}
    assert all(message.status == "processing" for message in messages[:-1])
    final = messages[-1]
    assert final.status == "completed"
    assert final.total == final.completed == 3
    first = final.web_info_list[0]
    assert (first.source_url, first.title) == ("https://a.com/0", "r0")
    assert first.content.startswith("# r0")


def test_large_crawl_reads_past_one_api_page():
    handler, _ = crawl_api(pages(120))
    assert len(run(handler, {"limit": 120})[-1].web_info_list) == 120


def test_short_api_pages_do_not_end_the_crawl_early():
    handler, _ = crawl_api(pages(7), page_size=2)
    assert len(run(handler)[-1].web_info_list) == 7


def test_failed_crawl_raises():
    handler, _ = crawl_api(pages(1), statuses=("failed",))
    with pytest.raises(OlostepError, match="failed"):
        run(handler)


def test_crawl_options_map_the_form():
    assert crawl_options({"limit": 500, "max_depth": 2, "include_paths": "/docs/**, /blog/*", "exclude_paths": "/x/*"}) == {
        "max_pages": 500,
        "max_depth": 2,
        "include_urls": ["/docs/**", "/blog/*"],
        "exclude_urls": ["/x/*"],
    }
    assert crawl_options({"limit": 500, "crawl_subpages": False, "include_paths": "/docs/**"}) == {"max_pages": 1}
    assert crawl_options({})["max_pages"] == 10
    assert crawl_options({"limit": 100_000})["max_pages"] == 100_000
    assert crawl_options({"limit": 100_001})["max_pages"] == 100_000
    assert crawl_options({"max_depth": 0})["max_depth"] == 0


def test_split_patterns():
    assert split_patterns(" a, ,b ") == ["a", "b"]
    assert split_patterns(None) == []


def test_title_and_description():
    prose = "This is the first real sentence of the page content."
    assert title_and_description(f"Crawl - Olostep Docs\n\n> Index\n\n[home](x)\n\n{prose}", "u") == ("Crawl - Olostep Docs", prose)
    assert title_and_description(f"# Title\n\n{prose}", "u") == ("Title", prose)
    assert title_and_description("Short page", "https://a.com") == ("Short page", "")
    assert title_and_description("", "https://a.com") == ("https://a.com", "")


def test_invalid_key_message_never_contains_the_key():
    def handler(request):
        return httpx.Response(401, json={})

    with pytest.raises(OlostepError) as error:
        run(handler)
    assert "test-key" not in str(error.value)
