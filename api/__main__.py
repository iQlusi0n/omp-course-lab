"""``python -m api`` — serve the JSON API and web/ on http://127.0.0.1:8080."""

import argparse

from .db import db_path
from .server import SERVICE_NAME, VERSION, make_server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m api", description=SERVICE_NAME)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)

    server = make_server(args.host, args.port)
    print(f"{SERVICE_NAME} {VERSION} listening on http://{args.host}:{args.port} (db: {db_path()})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
