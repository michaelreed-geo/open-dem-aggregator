"""
Module of functions used to interact with web hosted data, including requests and downloads.
"""

import http.client
import json
import urllib.parse
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from http import HTTPMethod
from pathlib import Path


def https_request(
    url: str,
    method: HTTPMethod = HTTPMethod.GET,
    headers: dict | None = None,
    body: dict | None = None,
    decoding_codec: str | None = "utf-8",
) -> bytes | str:
    """
    Generic function for HTTPS requests. Supports any HTTPS method (GET, POST, HEAD, etc.),
    with arguments for passing headers or body to the request. Returns data from the request.

    Args:
        url (str): URL to request.
        method (HTTPMethod, optional): HTTPS method (GET, POST, HEAD, etc.). Defaults to GET.
        headers (dict or None, optional): Dictionary of headers to include in the request.
            Defaults to None.
        body (dict or None, optional): Dictionary of body or payload to send with the request.
            Defaults to None.
        decoding_codec (str or None, optional): Codec used to decode the returned data.
            Defaults to 'utf-8'. If None, the raw bytes are returned.

    Returns:
        str or bytes: Data returned by the request, decoded as a string if decoding_codec is set,
            or as bytes otherwise.
    """
    parsed_url = urllib.parse.urlparse(url)

    # convert body from dict to encoded str object
    if body:
        body = json.dumps(body)

    # convert None to empty dict so request does not TypeError
    if headers is None:
        headers = {}

    conn = http.client.HTTPSConnection(parsed_url.netloc)

    full_path = parsed_url.path
    if parsed_url.query:
        full_path += f"?{parsed_url.query}"

    conn.request(method, full_path, body, headers)
    response = conn.getresponse()
    # if codec specified, decode the data
    if decoding_codec:
        data = response.read().decode(decoding_codec)
    # if no codec specific, return data as bytes
    else:
        data = response.read()
    conn.close()
    return data


def https_download(
    url: str,
    chunk_size: int = 2048,
    output_path: Path | None = None,
    method: HTTPMethod = HTTPMethod.GET,
    headers: dict | None = None,
    body: dict | None = None,
) -> Path:
    """
    Downloads a file from the web via an HTTPS request.

    Supports streaming the response in chunks to avoid loading the full file into memory.
    The downloaded file is saved to the given path or a temporary location.

    Args:
        url (str): URL of the file to download.
        chunk_size (int, optional): Size (in bytes) of each streamed chunk. Defaults to 2048.
        output_path (Path or None, optional): Path to save the downloaded file.
            Can be a directory or a specific file path. If None, a temporary path will be used.
        method (HTTPMethod, optional): HTTP method to use (e.g., GET, POST). Defaults to GET.
        headers (dict or None, optional): Dictionary of headers to include in the request.
            Defaults to None.
        body (dict or None, optional): Request body/payload. Typically a dictionary for POST/PUT
            methods. Defaults to None.

    Returns:
        Path: Path to the downloaded file.
    """
    parsed_url = urllib.parse.urlparse(url)

    # convert body from dict to encoded str object
    if body:
        body = urllib.parse.urlencode(body)

    # convert None to empty dict so request does not TypeError
    if headers is None:
        headers = {}

    parsed_url = urllib.parse.urlparse(url)

    # convert body from dict to encoded str object
    if body:
        body = urllib.parse.urlencode(body)

    conn = http.client.HTTPSConnection(parsed_url.netloc)
    conn.request(method, parsed_url.path, body, headers)
    response = conn.getresponse()
    downloaded = 0

    file_name = "temp"
    if "." in Path(parsed_url.path).name:
        # if no filetype in url, use output_path from response
        file_name = Path(parsed_url.path).name
    elif "Content-Disposition" in response.headers:
        # else get file name from response
        cd_header = response.headers["Content-Disposition"]
        if "filename=" in cd_header:
            file_name = cd_header.split("filename=")[-1].strip('"')

    # if output path not specified, use Downloads folder and file name as specified in url
    if output_path is None:
        output_path = Path.home() / "Downloads" / file_name
    # if user provided directory, append url path name to user provided dir
    elif output_path.suffix == "":
        output_path = output_path / file_name
    # warn user if user provided output_path file type does not match url file type
    elif output_path.suffix != Path(parsed_url.path).suffix:
        warnings.warn(
            "\n"
            "File type of output_path does not match the expected file type. "
            "File may not function as expected without intervention.\n"
            f"File type provided={output_path.suffix}. "
            f"File type expected={Path(parsed_url.path).suffix}."
        )

    # warn user if output_path points to existing file that would be overridden
    if output_path.exists():
        raise UserWarning(
            f"File already exists at {str(output_path)}. \n"
            "Please delete, rename or move the existing file OR change the output_path. "
            "Then re-run your script."
        )

    # ensure file path is valid and exists - if it doesn't then make it
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # write to file in chunks
    with open(output_path, "wb") as out_file:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            print(f"Download progress {downloaded / 1024**2:.0f} MB", end="\r")
    print(f"Download finished {output_path}")
    conn.close()
    return output_path


def https_download_parallel(
    urls: list[str],
    output_dir: Path = Path.home() / "Downloads",
    chunk_size: int = 2048,
    method: HTTPMethod = HTTPMethod.GET,
    headers: list[dict] | None = None,
    body: list[dict] | None = None,
    max_workers: int = 5,
) -> list[Path]:
    """
    Downloads multiple files in parallel using multithreading.

    Each URL is downloaded concurrently using a thread pool. Optionally, headers and bodies can be
    supplied for each request. If provided, `headers` and `body` lists must match the length of
    `urls`.

    Args:
        urls (list[str]): List of URLs to download.
        output_dir (Path, optional): Directory where the downloaded files will be saved.
            Defaults to the user's Downloads folder.
        chunk_size (int, optional): Size (in bytes) of each streamed chunk. Defaults to 2048.
        method (HTTPMethod, optional): HTTP method to use for each request. Defaults to GET.
        headers (list[dict], optional): List of header dictionaries for each request.
            Defaults to empty list.
        body (list[dict], optional): List of body dictionaries (payloads) for each request.
            Defaults to empty list.
        max_workers (int, optional): Number of threads to use for concurrent downloads.
            Defaults to 5.

    Returns:
        list[Path]: List of file paths where the downloaded files were saved.
    """
    # create empty args if not supplied
    if not headers:
        headers = [{} for i in urls]
    if not body:
        body = [{} for i in urls]
    # check length of lists are equal
    if not len(urls) == len(headers) == len(body):
        raise IndexError(
            f"Length of input lists is invalid: urls={len(urls)}, headers={len(headers)}, "
            f"body={len(body)}."
        )

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(
                https_download, _url, chunk_size, output_dir, method, _headers, _body
            ): _url
            for _url, _headers, _body in zip(urls, headers, body)
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                print(f"Download failed for {url}: {exc}")
    return results
