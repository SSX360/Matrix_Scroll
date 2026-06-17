import requests

r = requests.post(
    "http://127.0.0.1:59712/api/chat",
    json={"message": "scan my project and summarize the stack", "history": []},
    stream=True,
    timeout=(5, 120),
)
text = []
for line in r.iter_lines(decode_unicode=True):
    if line and line.startswith("data:") and not line.startswith("data: ["):
        chunk = line[5:].strip().strip('"')
        if chunk and chunk not in ("event: done",):
            text.append(chunk)
    if len("".join(text)) > 500:
        break
print("".join(text)[:600])
