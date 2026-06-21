import time

import pinggy


def main():
    pinggy.disable_log()
    tunnel = pinggy.start_tunnel(
        "127.0.0.1:8000",
        type="http",
        httpsonly=True,
        allowpreflight=True,
    )

    url = ""
    for _ in range(90):
        urls = list(getattr(tunnel, "urls", None) or [])
        https_urls = [item for item in urls if str(item).startswith("https://")]
        if https_urls:
            url = str(https_urls[0])
            break
        if urls:
            url = str(urls[0])
            break
        time.sleep(1)

    if not url:
        raise RuntimeError("Pinggy tunnel started but no public URL was assigned.")

    print(url, flush=True)

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
