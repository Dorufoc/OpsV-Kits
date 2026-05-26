from __future__ import annotations

import logging
import os
import posixpath
import threading
import time
import urllib.parse
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional

import paramiko

from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class _WebDAVRequestHandler(BaseHTTPRequestHandler):
    server_version = "OpsV-Kits/1.0"
    sys_version = ""

    SSH_SERVICE = None

    def log_message(self, format, *args):
        logger.debug("WebDAV: %s - %s", self.client_address[0], format % args)

    def _parse_path(self):
        raw = urllib.parse.urlparse(self.path)
        parts = raw.path.strip("/").split("/")
        if not parts or not parts[0]:
            return None, "/"
        account_alias = urllib.parse.unquote(parts[0])
        remote_path = "/" + "/".join(urllib.parse.unquote(p) for p in parts[1:])
        return account_alias, remote_path

    def _get_sftp(self, alias: str):
        account = self.SSH_SERVICE.get_account(alias)
        if not account:
            return None, None
        try:
            conn = self.SSH_SERVICE.pool.get_connection(account)
            sftp = conn.conn.open_sftp()
            return sftp, conn
        except Exception as e:
            logger.error("Failed to get SFTP for %s: %s", alias, e)
            return None, None

    def _release(self, conn):
        if conn:
            try:
                self.SSH_SERVICE.pool.release_connection(conn)
            except Exception:
                pass

    def _close_sftp(self, sftp):
        if sftp:
            try:
                sftp.close()
            except Exception:
                pass

    def _format_time(self, t: float) -> str:
        dt = datetime.fromtimestamp(t, tz=timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

    def _list_accounts_xml(self):
        accounts = self.SSH_SERVICE.list_accounts() or []
        lines = []
        lines.append('<?xml version="1.0" encoding="utf-8"?>')
        lines.append('<D:multistatus xmlns:D="DAV:">')
        for acct in accounts:
            alias = acct.alias
            href = f"/{urllib.parse.quote(alias, safe='')}/"
            lines.append("<D:response>")
            lines.append(f"  <D:href>{href}</D:href>")
            lines.append("  <D:propstat>")
            lines.append("    <D:prop>")
            lines.append(f"      <D:displayname>{_xml_escape(alias)}</D:displayname>")
            lines.append("      <D:resourcetype><D:collection/></D:resourcetype>")
            lines.append("      <D:getcontenttype>httpd/unix-directory</D:getcontenttype>")
            lines.append("      <D:getcontentlength>0</D:getcontentlength>")
            lines.append("    </D:prop>")
            lines.append("    <D:status>HTTP/1.1 200 OK</D:status>")
            lines.append("  </D:propstat>")
            lines.append("</D:response>")
        lines.append("</D:multistatus>")
        return "\n".join(lines)

    def _stat_to_xml(self, alias: str, remote_path: str, stat: paramiko.SFTPAttributes, is_root: bool = False):
        if is_root:
            href = f"/{urllib.parse.quote(alias, safe='')}/"
            name = alias
        else:
            parts = remote_path.strip("/").split("/")
            name = parts[-1] if parts else alias
            encoded_parts = [urllib.parse.quote(alias, safe='')] + [urllib.parse.quote(p, safe='') for p in parts]
            href = "/" + "/".join(encoded_parts)
            if stat.st_mode is not None and stat.st_mode & 0o40000:
                href += "/"

        is_dir = stat.st_mode is not None and stat.st_mode & 0o40000
        if is_dir:
            content_type = "httpd/unix-directory"
            content_length = 0
            res_type = "<D:collection/>"
        else:
            content_type = "application/octet-stream"
            content_length = stat.st_size or 0
            res_type = ""

        mtime = self._format_time(stat.st_mtime if stat.st_mtime else time.time())

        return f"""<D:response>
  <D:href>{href}</D:href>
  <D:propstat>
    <D:prop>
      <D:displayname>{_xml_escape(name)}</D:displayname>
      <D:resourcetype>{res_type}</D:resourcetype>
      <D:getcontenttype>{content_type}</D:getcontenttype>
      <D:getcontentlength>{content_length}</D:getcontentlength>
      <D:getlastmodified>{mtime}</D:getlastmodified>
    </D:prop>
    <D:status>HTTP/1.1 200 OK</D:status>
  </D:propstat>
</D:response>"""

    def _handle_propfind_root(self):
        body = self._list_accounts_xml()
        self.send_response(207)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.send_header("DAV", "1, 2")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _handle_propfind(self, alias: str, remote_path: str):
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self.send_error(404, "Account not found or connection failed")
            return
        try:
            stat_info = sftp.stat(remote_path)
            if stat_info.st_mode is not None and stat_info.st_mode & 0o40000:
                items = sftp.listdir_attr(remote_path)
                lines = []
                lines.append('<?xml version="1.0" encoding="utf-8"?>')
                lines.append('<D:multistatus xmlns:D="DAV:">')
                lines.append(self._stat_to_xml(alias, remote_path, stat_info))
                base_path = remote_path.rstrip("/")
                for item in items:
                    item_path = posixpath.join(base_path, item.filename) if base_path else "/" + item.filename
                    lines.append(self._stat_to_xml(alias, item_path, item))
                lines.append("</D:multistatus>")
                body = "\n".join(lines)
            else:
                body = self._stat_to_xml(alias, remote_path, stat_info)
                body = f"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:">
{body}
</D:multistatus>"""

            self.send_response(207)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Content-Length", str(len(body.encode("utf-8"))))
            self.send_header("DAV", "1, 2")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
        except FileNotFoundError:
            self.send_error(404, "Path not found")
        except PermissionError:
            self.send_error(403, "Permission denied")
        except OSError as e:
            logger.error("PROPFIND OS error: %s", e)
            self.send_error(404, str(e))
        except Exception as e:
            logger.error("PROPFIND error: %s", e)
            self.send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_get(self, alias: str, remote_path: str):
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self.send_error(404, "Account not found or connection failed")
            return
        try:
            stat_info = sftp.stat(remote_path)
            if stat_info.st_mode is not None and stat_info.st_mode & 0o40000:
                self.send_response(302)
                self.send_header("Location", self.path.rstrip("/") + "/")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(stat_info.st_size))
            self.send_header("Content-Disposition", f'inline; filename="{os.path.basename(remote_path)}"')
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with sftp.open(remote_path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except FileNotFoundError:
            self.send_error(404, "File not found")
        except PermissionError:
            self.send_error(403, "Permission denied")
        except Exception as e:
            logger.error("GET error: %s", e)
            self.send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_put(self, alias: str, remote_path: str):
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self.send_error(404, "Account not found or connection failed")
            return
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(content_length) if content_length > 0 else b""
            remote_dir = posixpath.dirname(remote_path)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                self._mkdir_p(sftp, remote_dir)
            with sftp.open(remote_path, "wb") as f:
                f.write(data)
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()
        except Exception as e:
            logger.error("PUT error: %s", e)
            self.send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_delete(self, alias: str, remote_path: str):
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self.send_error(404, "Account not found or connection failed")
            return
        try:
            stat_info = sftp.stat(remote_path)
            if stat_info.st_mode is not None and stat_info.st_mode & 0o40000:
                self._rmtree(sftp, remote_path)
            else:
                sftp.remove(remote_path)
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
        except FileNotFoundError:
            self.send_error(404, "Path not found")
        except PermissionError:
            self.send_error(403, "Permission denied")
        except Exception as e:
            logger.error("DELETE error: %s", e)
            self.send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_mkcol(self, alias: str, remote_path: str):
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self.send_error(404, "Account not found or connection failed")
            return
        try:
            sftp.mkdir(remote_path)
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()
        except Exception as e:
            logger.error("MKCOL error: %s", e)
            self.send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_move(self, alias: str, remote_path: str):
        dest_header = self.headers.get("Destination", "")
        if not dest_header:
            self.send_error(400, "Destination header required")
            return
        parsed_dest = urllib.parse.urlparse(dest_header)
        dest_parts = parsed_dest.path.strip("/").split("/")
        if not dest_parts or urllib.parse.unquote(dest_parts[0]) != alias:
            self.send_error(502, "Cross-account move not supported")
            return
        dest_path = "/" + "/".join(urllib.parse.unquote(p) for p in dest_parts[1:])
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self.send_error(404, "Account not found or connection failed")
            return
        try:
            sftp.rename(remote_path, dest_path)
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
        except Exception as e:
            logger.error("MOVE error: %s", e)
            self.send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _mkdir_p(self, sftp, path: str):
        parts = path.strip("/").split("/")
        current = ""
        for part in parts:
            if not part:
                continue
            current = posixpath.join(current, part) if current else "/" + part
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)

    def _rmtree(self, sftp, path: str):
        for item in sftp.listdir_attr(path):
            item_path = posixpath.join(path, item.filename)
            if item.st_mode & 0o40000:
                self._rmtree(sftp, item_path)
            else:
                sftp.remove(item_path)
        sftp.rmdir(path)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("DAV", "1, 2")
        self.send_header("MS-Author-Via", "DAV")
        self.send_header("Allow", "OPTIONS, GET, HEAD, PUT, DELETE, PROPFIND, MKCOL, MOVE, COPY")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_PROPFIND(self):
        alias, remote_path = self._parse_path()
        if alias is None:
            self._handle_propfind_root()
        else:
            self._handle_propfind(alias, remote_path)

    def do_GET(self):
        alias, remote_path = self._parse_path()
        if alias is None:
            self._list_root_html()
        else:
            self._handle_get(alias, remote_path)

    def do_HEAD(self):
        alias, remote_path = self._parse_path()
        if alias is None:
            self.send_response(200)
            self.end_headers()
        else:
            sftp, conn = self._get_sftp(alias)
            if not sftp:
                self.send_error(404)
                return
            try:
                stat_info = sftp.stat(remote_path)
                self.send_response(200)
                self.send_header("Content-Length", str(stat_info.st_size))
                self.end_headers()
            except FileNotFoundError:
                self.send_error(404)
            except Exception as e:
                self.send_error(500)
            finally:
                self._close_sftp(sftp)
                self._release(conn)

    def do_PUT(self):
        alias, remote_path = self._parse_path()
        if alias is None:
            self.send_error(400, "Account alias required")
        else:
            self._handle_put(alias, remote_path)

    def do_DELETE(self):
        alias, remote_path = self._parse_path()
        if alias is None:
            self.send_error(400, "Account alias required")
        else:
            self._handle_delete(alias, remote_path)

    def do_MKCOL(self):
        alias, remote_path = self._parse_path()
        if alias is None:
            self.send_error(400, "Account alias required")
        else:
            self._handle_mkcol(alias, remote_path)

    def do_MOVE(self):
        alias, remote_path = self._parse_path()
        if alias is None:
            self.send_error(400, "Account alias required")
        else:
            self._handle_move(alias, remote_path)

    def _list_root_html(self):
        accounts = self.SSH_SERVICE.list_accounts() or []
        items = "".join(
            f'<li><a href="/{urllib.parse.quote(a.alias, safe="")}/">{_xml_escape(a.alias)}</a>'
            f' ({_xml_escape(a.host or "")}:{a.port or 22})</li>'
            for a in accounts
        )
        body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>OpsV-Kits Remote Drives</title>
<style>
body {{ font-family: sans-serif; margin: 2em; }}
h1 {{ color: #409eff; }}
ul {{ list-style: none; padding: 0; }}
li {{ padding: 8px; margin: 4px 0; background: #f5f7fa; border-radius: 4px; }}
a {{ color: #409eff; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>OpsV-Kits Remote Drives</h1>
<p>Available remote servers:</p>
<ul>{items}</ul>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


class RemoteDriveService:
    def __init__(self):
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, host: str = "127.0.0.1", port: int = 8081) -> bool:
        with self._lock:
            if self._running:
                return True
            try:
                _WebDAVRequestHandler.SSH_SERVICE = ssh_account_service
                self._server = ThreadingHTTPServer((host, port), _WebDAVRequestHandler)
                self._thread = threading.Thread(
                    target=self._server.serve_forever,
                    daemon=True,
                    name="remote-drive-webdav",
                )
                self._thread.start()
                self._running = True
                logger.info("Remote Drive WebDAV server started on %s:%s", host, port)
                return True
            except Exception as e:
                logger.error("Failed to start Remote Drive WebDAV server: %s", e)
                self._running = False
                return False

    def stop(self) -> None:
        with self._lock:
            if self._server:
                try:
                    self._server.shutdown()
                except Exception:
                    pass
                try:
                    self._server.server_close()
                except Exception:
                    pass
                self._server = None
            self._running = False
            self._thread = None
            logger.info("Remote Drive WebDAV server stopped")

    def restart(self, host: str = "127.0.0.1", port: int = 8081) -> bool:
        self.stop()
        time.sleep(0.5)
        return self.start(host, port)


remote_drive_service = RemoteDriveService()
