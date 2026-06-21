# Cookie Testing

This project can test whether your local XipuAI login state is still usable. The test runs only on your own computer and does not upload cookie values to GitHub.

## 1. Generate local login state

```bash
xjgpt-login
```

or:

```bash
python login_once.py
```

After the browser opens, log in to XipuAI manually. When the chat page is visible, return to the terminal and press Enter. This creates:

```text
school_gpt_state.json
```

Do not upload this file. It contains your local login state.

## 2. Test whether cookies can enter XipuAI

```bash
python scripts/test_cookies.py
```

Expected successful output:

```text
[OK] Found related cookie(s). Values are hidden.
[OK] The saved cookie/state appears usable for the XipuAI web page.
```

If it reports a login page, run `xjgpt-login` again because the login state has expired.

## 3. Open a visible browser for debugging

```bash
python scripts/test_cookies.py --show-browser
```

This is useful when the script cannot identify whether the page is the chat page or the login page.

## 4. Test direct HTTP API access

Cookie-based direct API access requires the real XipuAI backend endpoint. The page URL `https://xipuai.xjtlu.edu.cn/v3/chat` is not necessarily the backend API endpoint.

After you identify the real backend endpoint from the browser Network panel, you can test it with:

```bash
python scripts/test_cookies.py \
  --api-endpoint "https://xipuai.xjtlu.edu.cn/YOUR/REAL/API/PATH" \
  --api-method POST \
  --payload examples/chat_request.example.json
```

The script will send the request using the cookies from `school_gpt_state.json` and print the HTTP status plus a short response preview.

## 5. Security notes

- The script does not print cookie values.
- `school_gpt_state.json` must stay local.
- Do not commit cookie files, request captures containing tokens, or private HAR files.
- This test is only for your own authorised XipuAI account/session.
