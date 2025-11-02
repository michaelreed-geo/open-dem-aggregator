import json
import warnings
from http import HTTPMethod
from unittest import mock

import pytest

from odemagg.web import https_download, https_download_parallel, https_request


@pytest.fixture
def mock_https_connection():
    with mock.patch("http.client.HTTPSConnection") as mock_conn_class:
        mock_conn = mock_conn_class.return_value
        mock_response = mock.Mock()
        mock_response.read.return_value = b'{"status":"ok"}'
        mock_response.getheaders.return_value = []
        mock_response.headers = {}
        mock_conn.getresponse.return_value = mock_response
        yield mock_conn, mock_response


def test_https_request_get(mock_https_connection):
    conn, response = mock_https_connection
    response.read.return_value = b'{"result":"success"}'

    result = https_request("https://example.com/api")

    conn.request.assert_called_once_with("GET", "/api", None, {})
    assert result == '{"result":"success"}'


def test_https_request_post_with_body(mock_https_connection):
    conn, response = mock_https_connection
    response.read.return_value = b'{"status":"posted"}'

    result = https_request(
        "https://example.com/api",
        method=HTTPMethod.POST,
        body={"key": "value"},
        headers={"Content-Type": "application/json"},
    )

    body_sent = json.dumps({"key": "value"})
    conn.request.assert_called_once_with(
        "POST", "/api", body_sent, {"Content-Type": "application/json"}
    )
    assert result == '{"status":"posted"}'


def test_https_request_no_decoding(mock_https_connection):
    conn, response = mock_https_connection
    response.read.return_value = b"\x00binarydata"

    result = https_request("https://example.com/api", decoding_codec=None)

    assert isinstance(result, bytes)
    assert result == b"\x00binarydata"


def test_https_download(tmp_path, mock_https_connection):
    conn, response = mock_https_connection
    content = b"TestData" * 10
    response.read.side_effect = [content, b""]  # simulate chunked reads
    response.headers = {}

    url = "https://example.com/testfile.txt"
    path = https_download(url, output_path=tmp_path / "testfile.txt")

    assert path.exists()
    assert path.read_bytes() == content
    assert path.name == "testfile.txt"


def test_https_download_warns_on_suffix_mismatch(tmp_path, mock_https_connection):
    conn, response = mock_https_connection
    response.read.side_effect = [b"data", b""]
    response.headers = {}

    file_path = tmp_path / "file.csv"
    url = "https://example.com/test.json"

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        https_download(url, output_path=file_path)

        assert any(
            "File type of output_path does not match" in str(warn.message) for warn in w
        )


def test_https_download_fails_if_file_exists(tmp_path, mock_https_connection):
    file_path = tmp_path / "file.txt"
    file_path.write_text("existing")

    url = "https://example.com/file.txt"

    with pytest.raises(UserWarning, match="File already exists"):
        https_download(url, output_path=file_path)


def test_https_download_parallel_success(tmp_path):
    with mock.patch("odemagg.web.https_download") as mock_download:
        mock_download.side_effect = lambda *args, **kwargs: tmp_path / "file.txt"

        urls = ["https://example.com/file1", "https://example.com/file2"]
        result_paths = https_download_parallel(urls, output_dir=tmp_path)

        assert len(result_paths) == 2
        assert all(path.name == "file.txt" for path in result_paths)
        assert mock_download.call_count == 2
