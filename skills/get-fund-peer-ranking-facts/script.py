#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main():
    config = {}
    payload = {}
    try:
        base_dir = Path(__file__).resolve().parent
        config = json.loads((base_dir / "config.json").read_text(encoding="utf-8"))
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError("输入必须是 JSON 对象")
        endpoint = (
            config["java_base_url"].rstrip("/")
            + "/skills/"
            + config["skill_id"]
        )
        request_payload = {"data": payload}
        request = Request(endpoint, json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
                          {"Content-Type": "application/json; charset=utf-8"}, method="POST")
        try:
            with urlopen(request, timeout=int(config.get("timeout_seconds", 20))) as response:
                status, body = response.status, response.read()
        except HTTPError as error:
            status, body = error.code, error.read()
        response = json.loads(body.decode("utf-8"))
        result = response.get("data") if isinstance(response, dict) and isinstance(response.get("data"), dict) else response
        if not isinstance(result, dict):
            raise ValueError("Java Skill 服务返回 data 必须是 JSON 对象")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if 200 <= status < 300 and result.get("success") is True else 1
    except URLError as error:
        message = f"无法连接 Java Skill 服务: {error.reason}"
    except Exception as error:
        message = str(error)
    print(json.dumps({"success": False, "skill_id": config.get("skill_id"),
                      "input": payload, "message": message}, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
