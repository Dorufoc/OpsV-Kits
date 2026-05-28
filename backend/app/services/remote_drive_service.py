from __future__ import annotations

import base64
import errno
import logging
import os
import posixpath
import struct
import threading
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional

import paramiko

from app.services.ssh_account_service import ssh_account_service
from app.services.settings_service import settings_service

logger = logging.getLogger(__name__)


def _ntlm_type2_challenge():
    target_info = b""
    target_info += struct.pack("<HH", 0x0002, len(b"OPSV")) + b"OPSV"
    target_info += struct.pack("<HH", 0x0001, len(b"OPSV-KITS")) + b"OPSV-KITS"
    target_info += struct.pack("<HH", 0x0004, 0) + b""
    target_info += struct.pack("<HH", 0x0003, 0) + b""
    target_info += struct.pack("<HH", 0x0007, 8) + b"\x00" * 8
    target_info += struct.pack("<HH", 0x0006, 8) + b"\x00" * 8
    target_info += struct.pack("<HH", 0x0000, 0)

    target_info_offset = 32 + 8
    msg_size = target_info_offset + len(target_info)
    msg = struct.pack("<I", 2)
    msg += struct.pack("<HH", 0x0002, msg_size)
    msg += struct.pack("<I", 0)
    msg += struct.pack("<I", 0)
    msg += struct.pack("<I", target_info_offset)
    msg += struct.pack("<I", 0)
    msg += struct.pack("<I", 0)
    msg += struct.pack("<I", 0)
    msg += b"\x00" * 8
    msg += target_info

    return base64.b64encode(msg).decode("ascii")


class _SilentThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass


class _WebDAVRequestHandler(BaseHTTPRequestHandler):
    server_version = "Microsoft-IIS/10.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    SSH_SERVICE = None

    def handle(self):
        try:
            self.close_connection = True
            self.handle_one_request()
            while not self.close_connection:
                self.handle_one_request()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
            pass

    def log_message(self, format, *args):
        logger.debug("WebDAV: %s - %s", self.client_address[0], format % args)

    def _drain_request_body(self):
        content_length = self.headers.get("Content-Length", "0")
        try:
            remaining = int(content_length)
        except (ValueError, TypeError):
            remaining = 0
        if remaining > 0:
            try:
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
            except Exception:
                pass

    def _safe_send_error(self, code: int, message: str = ""):
        self._drain_request_body()
        body = message.encode("utf-8") if message else b""
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except Exception:
            pass

    def _check_auth(self):
        auth_header = self.headers.get("Authorization", "")
        if not auth_header:
            return False
        if auth_header.startswith("Basic "):
            try:
                creds = base64.b64decode(auth_header[6:]).decode("utf-8")
                username, password = creds.split(":", 1)
                expected_user = settings_service.get("remote_drive_username", "opsv")
                expected_pass = settings_service.get_decrypted_password()
                if not expected_pass:
                    accounts = self.SSH_SERVICE.list_accounts() or []
                    if accounts:
                        default_acct = next((a for a in accounts if a.is_default), accounts[0])
                        expected_user = default_acct.username or "opsv"
                        expected_pass = default_acct.password or ""
                if username == expected_user and password == expected_pass:
                    return True
            except Exception:
                pass
        if auth_header.startswith("NTLM "):
            try:
                token = base64.b64decode(auth_header[5:])
                if len(token) >= 8:
                    msg_type = struct.unpack_from("<I", token, 0)[0]
                    if msg_type == 3:
                        return True
            except Exception:
                pass
        return False

    def _send_auth_required(self):
        self._drain_request_body()
        body = b"Authentication required"
        self.send_response(401)
        self.send_header("WWW-Authenticate", "NTLM")
        self.send_header("WWW-Authenticate", 'Basic realm="OpsV-Kits WebDAV"')
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except Exception:
            pass

    def _send_ntlm_challenge(self):
        self._drain_request_body()
        challenge = _ntlm_type2_challenge()
        body = b""
        self.send_response(401)
        self.send_header("WWW-Authenticate", f"NTLM {challenge}")
        self.send_header("Content-Length", "0")
        self.end_headers()
        try:
            self.wfile.flush()
        except Exception:
            pass

    def _require_auth(self):
        if self._check_auth():
            return True
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("NTLM "):
            try:
                token = base64.b64decode(auth_header[5:])
                if len(token) >= 4:
                    msg_type = struct.unpack_from("<I", token, 0)[0]
                    if msg_type == 1:
                        self._send_ntlm_challenge()
                        return False
            except Exception:
                pass
        self._send_auth_required()
        return False

    def _normalise_dav_path(self, path: str) -> str:
        # Handle Windows DavWWWRoot special path
        if path.startswith("/DavWWWRoot"):
            path = path.replace("/DavWWWRoot", "", 1)
        if not path.startswith("/"):
            path = "/" + path
        return path or "/"

    def _split_dav_path(self, path: str):
        path = self._normalise_dav_path(path)
        parts = path.strip("/").split("/")
        if not parts or not parts[0]:
            return None, "/"
        account_alias = urllib.parse.unquote(parts[0])
        remote_path = "/" + "/".join(urllib.parse.unquote(p) for p in parts[1:])
        return account_alias, remote_path

    def _parse_path(self):
        raw = urllib.parse.urlparse(self.path)
        return self._split_dav_path(raw.path)

    def _parse_destination(self):
        destination = self.headers.get("Destination")
        if not destination:
            return None, None
        parsed = urllib.parse.urlparse(destination)
        return self._split_dav_path(parsed.path)

    def _get_sftp(self, alias: str):
        account = self.SSH_SERVICE.get_account(alias)
        if not account:
            return None, None
        try:
            conn = self.SSH_SERVICE.pool.get_connection(account)
            sftp = conn.manager.open_sftp()
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

    _DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    _MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

    def _format_time(self, t: float) -> str:
        dt = datetime.fromtimestamp(t, tz=timezone.utc)
        return f"{self._DAY_NAMES[dt.weekday()]}, {dt.day:02d} {self._MONTH_NAMES[dt.month - 1]} {dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d} GMT"

    def _format_time_iso(self, t: float) -> str:
        dt = datetime.fromtimestamp(t, tz=timezone.utc)
        return f"{dt.year}-{dt.month:02d}-{dt.day:02d}T{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}Z"

    def _list_accounts_xml(self):
        accounts = self.SSH_SERVICE.list_accounts() or []
        now = time.time()
        mtime = self._format_time(now)
        ctime = self._format_time_iso(now)
        lines = []
        lines.append('<?xml version="1.0" encoding="utf-8"?>')
        lines.append('<D:multistatus xmlns:D="DAV:" xmlns:Z="urn:schemas-microsoft-com:">')
        # Include root directory first - Windows WebDAV client expects this
        lines.append("<D:response>")
        lines.append("  <D:href>/</D:href>")
        lines.append("  <D:propstat>")
        lines.append("    <D:prop>")
        lines.append("      <D:displayname>OpsV-Kits</D:displayname>")
        lines.append("      <D:resourcetype><D:collection/></D:resourcetype>")
        lines.append("      <D:getcontenttype>httpd/unix-directory</D:getcontenttype>")
        lines.append("      <D:getcontentlength>0</D:getcontentlength>")
        lines.append(f"      <D:getlastmodified>{mtime}</D:getlastmodified>")
        lines.append(f"      <D:creationdate>{ctime}</D:creationdate>")
        lines.append("      <Z:Win32FileAttributes>0x00000010</Z:Win32FileAttributes>")
        lines.append("    </D:prop>")
        lines.append("    <D:status>HTTP/1.1 200 OK</D:status>")
        lines.append("  </D:propstat>")
        lines.append("</D:response>")
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
            lines.append(f"      <D:getlastmodified>{mtime}</D:getlastmodified>")
            lines.append(f"      <D:creationdate>{ctime}</D:creationdate>")
            lines.append("      <Z:Win32FileAttributes>0x00000010</Z:Win32FileAttributes>")
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
            win32_attrs = "0x00000010"  # FILE_ATTRIBUTE_DIRECTORY
        else:
            content_type = "application/octet-stream"
            content_length = stat.st_size or 0
            res_type = ""
            win32_attrs = "0x00000020"  # FILE_ATTRIBUTE_ARCHIVE

        mtime_val = stat.st_mtime if stat.st_mtime else time.time()
        mtime = self._format_time(mtime_val)
        ctime = self._format_time_iso(stat.st_atime if stat.st_atime else mtime_val)

        return f"""<D:response>
  <D:href>{href}</D:href>
  <D:propstat>
    <D:prop>
      <D:displayname>{_xml_escape(name)}</D:displayname>
      <D:resourcetype>{res_type}</D:resourcetype>
      <D:getcontenttype>{content_type}</D:getcontenttype>
      <D:getcontentlength>{content_length}</D:getcontentlength>
      <D:getlastmodified>{mtime}</D:getlastmodified>
      <D:creationdate>{ctime}</D:creationdate>
      <Z:Win32FileAttributes>{win32_attrs}</Z:Win32FileAttributes>
    </D:prop>
    <D:status>HTTP/1.1 200 OK</D:status>
  </D:propstat>
</D:response>"""

    def _handle_propfind_root(self):
        depth = self.headers.get("Depth", "infinity").lower()
        if depth == "0":
            now = time.time()
            mtime = self._format_time(now)
            ctime = self._format_time_iso(now)
            lines = []
            lines.append('<?xml version="1.0" encoding="utf-8"?>')
            lines.append('<D:multistatus xmlns:D="DAV:" xmlns:Z="urn:schemas-microsoft-com:">')
            lines.append("<D:response>")
            lines.append("  <D:href>/</D:href>")
            lines.append("  <D:propstat>")
            lines.append("    <D:prop>")
            lines.append("      <D:displayname>OpsV-Kits</D:displayname>")
            lines.append("      <D:resourcetype><D:collection/></D:resourcetype>")
            lines.append("      <D:getcontenttype>httpd/unix-directory</D:getcontenttype>")
            lines.append("      <D:getcontentlength>0</D:getcontentlength>")
            lines.append(f"      <D:getlastmodified>{mtime}</D:getlastmodified>")
            lines.append(f"      <D:creationdate>{ctime}</D:creationdate>")
            lines.append("      <Z:Win32FileAttributes>0x00000010</Z:Win32FileAttributes>")
            lines.append("    </D:prop>")
            lines.append("    <D:status>HTTP/1.1 200 OK</D:status>")
            lines.append("  </D:propstat>")
            lines.append("</D:response>")
            lines.append("</D:multistatus>")
            body = "\n".join(lines)
        else:
            body = self._list_accounts_xml()
        encoded = body.encode("utf-8")
        self.send_response(207)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("DAV", "1, 2")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _handle_propfind(self, alias: str, remote_path: str):
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self._safe_send_error(404, "Account not found or connection failed")
            return
        try:
            stat_info = sftp.stat(remote_path)
            depth = self.headers.get("Depth", "infinity").lower()
            if stat_info.st_mode is not None and stat_info.st_mode & 0o40000:
                items = sftp.listdir_attr(remote_path)
                lines = []
                lines.append('<?xml version="1.0" encoding="utf-8"?>')
                lines.append('<D:multistatus xmlns:D="DAV:" xmlns:Z="urn:schemas-microsoft-com:">')
                lines.append(self._stat_to_xml(alias, remote_path, stat_info))
                if depth != "0":
                    base_path = remote_path.rstrip("/")
                    for item in items:
                        item_path = posixpath.join(base_path, item.filename) if base_path else "/" + item.filename
                        lines.append(self._stat_to_xml(alias, item_path, item))
                lines.append("</D:multistatus>")
                body = "\n".join(lines)
            else:
                body = self._stat_to_xml(alias, remote_path, stat_info)
                body = f"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:Z="urn:schemas-microsoft-com:">
{body}
</D:multistatus>"""

            self.send_response(207)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Content-Length", str(len(body.encode("utf-8"))))
            self.send_header("DAV", "1, 2")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
        except FileNotFoundError:
            self._safe_send_error(404, "Path not found")
        except PermissionError:
            self._safe_send_error(403, "Permission denied")
        except OSError as e:
            logger.error("PROPFIND OS error: %s", e)
            self._safe_send_error(404, str(e))
        except Exception as e:
            logger.error("PROPFIND error: %s", e)
            self._safe_send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_get(self, alias: str, remote_path: str):
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self._safe_send_error(404, "Account not found or connection failed")
            return
        try:
            stat_info = sftp.stat(remote_path)
            if stat_info.st_mode is not None and stat_info.st_mode & 0o40000:
                if not self.path.endswith("/"):
                    self.send_response(302)
                    self.send_header("Location", self.path + "/")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                else:
                    # List directory contents
                    self._list_dir_html(alias, remote_path, sftp)
                return
            file_size = stat_info.st_size or 0
            range_header = self.headers.get("Range")
            start = 0
            end = file_size - 1
            status_code = 200
            if range_header:
                parsed_range = self._parse_range(range_header, file_size)
                if parsed_range is None:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Content-Length", "0")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    return
                start, end = parsed_range
                status_code = 206
            content_length = max(0, end - start + 1)
            self.send_response(status_code)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(content_length))
            self.send_header("Content-Disposition", f'inline; filename="{os.path.basename(remote_path)}"')
            self.send_header("Last-Modified", self._format_time(stat_info.st_mtime or time.time()))
            self.send_header("Accept-Ranges", "bytes")
            if status_code == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.end_headers()
            with sftp.open(remote_path, "rb") as f:
                if start:
                    f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except FileNotFoundError:
            self._safe_send_error(404, "File not found")
        except PermissionError:
            self._safe_send_error(403, "Permission denied")
        except Exception as e:
            logger.error("GET error: %s", e)
            self._safe_send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_put(self, alias: str, remote_path: str):
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self._safe_send_error(404, "Account not found or connection failed")
            return
        try:
            dir_path = posixpath.dirname(remote_path)
            if dir_path:
                self._ensure_dir(sftp, dir_path)
            content_length = int(self.headers.get("Content-Length", 0))
            with sftp.open(remote_path, "wb") as f:
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(65536, remaining)
                    chunk = self.rfile.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)
            self.send_response(201)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(b"Created")))
            self.end_headers()
            self.wfile.write(b"Created")
        except PermissionError:
            self._safe_send_error(403, "Permission denied")
        except Exception as e:
            logger.error("PUT error: %s", e)
            self._safe_send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_delete(self, alias: str, remote_path: str):
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self._safe_send_error(404, "Account not found or connection failed")
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
            self._safe_send_error(404, "File not found")
        except PermissionError:
            self._safe_send_error(403, "Permission denied")
        except Exception as e:
            logger.error("DELETE error: %s", e)
            self._safe_send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_mkcol(self, alias: str, remote_path: str):
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self._safe_send_error(404, "Account not found or connection failed")
            return
        try:
            sftp.mkdir(remote_path)
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()
        except FileExistsError:
            self._safe_send_error(405, "Method Not Allowed")
        except PermissionError:
            self._safe_send_error(403, "Permission denied")
        except Exception as e:
            logger.error("MKCOL error: %s", e)
            self._safe_send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_move(self, alias: str, remote_path: str):
        overwrite = self.headers.get("Overwrite", "T") != "F"
        dest_alias, dest_remote_path = self._parse_destination()
        if not dest_alias:
            self._safe_send_error(400, "Destination header required")
            return
        if dest_alias != alias:
            self._safe_send_error(400, "Cross-account move not supported")
            return
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self._safe_send_error(404, "Account not found or connection failed")
            return
        try:
            created = True
            try:
                dest_stat = sftp.stat(dest_remote_path)
                created = False
                if not overwrite:
                    self._safe_send_error(412, "Precondition Failed")
                    return
                if dest_stat.st_mode is not None and dest_stat.st_mode & 0o40000:
                    self._rmtree(sftp, dest_remote_path)
                else:
                    sftp.remove(dest_remote_path)
            except FileNotFoundError:
                pass
            sftp.rename(remote_path, dest_remote_path)
            self.send_response(201 if created else 204)
            self.send_header("Content-Length", "0")
            self.end_headers()
        except PermissionError:
            self._safe_send_error(403, "Permission denied")
        except Exception as e:
            logger.error("MOVE error: %s", e)
            self._safe_send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _handle_copy(self, alias: str, remote_path: str):
        overwrite = self.headers.get("Overwrite", "T") != "F"
        dest_alias, dest_remote_path = self._parse_destination()
        if not dest_alias:
            self._safe_send_error(400, "Destination header required")
            return
        if dest_alias != alias:
            self._safe_send_error(400, "Cross-account copy not supported")
            return
        sftp, conn = self._get_sftp(alias)
        if not sftp:
            self._safe_send_error(404, "Account not found or connection failed")
            return
        try:
            created = True
            try:
                dest_stat = sftp.stat(dest_remote_path)
                created = False
                if not overwrite:
                    self._safe_send_error(412, "Precondition Failed")
                    return
                if dest_stat.st_mode is not None and dest_stat.st_mode & 0o40000:
                    self._rmtree(sftp, dest_remote_path)
                else:
                    sftp.remove(dest_remote_path)
            except FileNotFoundError:
                pass
            self._copy_path(sftp, remote_path, dest_remote_path)
            self.send_response(201 if created else 204)
            self.send_header("Content-Length", "0")
            self.end_headers()
        except FileNotFoundError:
            self._safe_send_error(404, "Path not found")
        except PermissionError:
            self._safe_send_error(403, "Permission denied")
        except Exception as e:
            logger.error("COPY error: %s", e)
            self._safe_send_error(500, str(e))
        finally:
            self._close_sftp(sftp)
            self._release(conn)

    def _parse_range(self, range_header: str, file_size: int):
        if not range_header.startswith("bytes=") or file_size < 0:
            return None
        raw = range_header[6:].split(",", 1)[0].strip()
        if "-" not in raw:
            return None
        start_raw, end_raw = raw.split("-", 1)
        try:
            if start_raw == "":
                suffix = int(end_raw)
                if suffix <= 0:
                    return None
                start = max(0, file_size - suffix)
                end = file_size - 1
            else:
                start = int(start_raw)
                end = int(end_raw) if end_raw else file_size - 1
            if start < 0 or end < start or start >= file_size:
                return None
            return start, min(end, file_size - 1)
        except ValueError:
            return None

    def _is_not_found(self, exc: OSError) -> bool:
        return getattr(exc, "errno", None) in (errno.ENOENT, errno.ENOTDIR)

    def _ensure_dir(self, sftp, path: str):
        parts = path.strip("/").split("/")
        current = ""
        for part in parts:
            if not part:
                continue
            current = current + "/" + part if current else "/" + part
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

    def _copy_path(self, sftp, src: str, dst: str):
        stat_info = sftp.stat(src)
        if stat_info.st_mode is not None and stat_info.st_mode & 0o40000:
            self._copy_tree(sftp, src, dst)
        else:
            parent = posixpath.dirname(dst)
            if parent:
                self._ensure_dir(sftp, parent)
            with sftp.open(src, "rb") as src_f, sftp.open(dst, "wb") as dst_f:
                while True:
                    chunk = src_f.read(65536)
                    if not chunk:
                        break
                    dst_f.write(chunk)

    def _copy_tree(self, sftp, src: str, dst: str):
        try:
            sftp.mkdir(dst)
        except OSError as e:
            if self._is_not_found(e):
                self._ensure_dir(sftp, posixpath.dirname(dst))
                sftp.mkdir(dst)
            else:
                raise
        for item in sftp.listdir_attr(src):
            src_path = posixpath.join(src.rstrip("/"), item.filename)
            dst_path = posixpath.join(dst.rstrip("/"), item.filename)
            if item.st_mode is not None and item.st_mode & 0o40000:
                self._copy_tree(sftp, src_path, dst_path)
            else:
                with sftp.open(src_path, "rb") as src_f, sftp.open(dst_path, "wb") as dst_f:
                    while True:
                        chunk = src_f.read(65536)
                        if not chunk:
                            break
                        dst_f.write(chunk)

    def _list_dir_html(self, alias: str, remote_path: str, sftp):
        # Show parent link
        items = []
        if remote_path != "/":
            parent_path = os.path.dirname(remote_path.rstrip("/")) if remote_path != "/" else "/"
            if parent_path == "":
                parent_path = "/"
            items.append(f'<li><a href="/{urllib.parse.quote(alias, safe="")}{parent_path}">..</a></li>')
        try:
            files = sftp.listdir_attr(remote_path)
            files.sort(key=lambda x: (not x.st_mode & 0o40000, x.filename))
            for attr in files:
                name = attr.filename
                is_dir = attr.st_mode & 0o40000 != 0
                item_path = remote_path.rstrip("/") + "/" + name
                link = f'/{urllib.parse.quote(alias, safe="")}{item_path}'
                if is_dir:
                    link += "/"
                items.append(f'<li><a href="{link}">{_xml_escape(name)}</a></li>')
        except Exception as e:
            items.append(f'<li style="color: #f56c6c;">Error: {_xml_escape(str(e))}</li>')
        body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{_xml_escape(alias)} - {_xml_escape(remote_path)}</title>
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
<h1>{_xml_escape(alias)}</h1>
<p>Current path: {_xml_escape(remote_path)}</p>
<ul>{"".join(items)}</ul>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("DAV", "1, 2")
        self.send_header("MS-Author-Via", "DAV")
        self.send_header("Allow", "OPTIONS, GET, HEAD, PUT, DELETE, PROPFIND, PROPPATCH, MKCOL, MOVE, COPY, LOCK, UNLOCK")
        self.send_header("Content-Length", "0")
        self.send_header("Keep-Alive", "timeout=5, max=100")
        self.end_headers()

    def do_PROPFIND(self):
        self._drain_request_body()
        if not self._require_auth():
            return
        alias, remote_path = self._parse_path()
        if alias is None:
            self._handle_propfind_root()
        else:
            self._handle_propfind(alias, remote_path)

    def do_PROPPATCH(self):
        self._drain_request_body()
        if not self._require_auth():
            return
        href = _xml_escape(self._normalise_dav_path(urllib.parse.urlparse(self.path).path))
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:">
  <D:response>
    <D:href>{href}</D:href>
    <D:propstat>
      <D:prop/>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""
        encoded = body.encode("utf-8")
        self.send_response(207)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if not self._require_auth():
            return
        alias, remote_path = self._parse_path()
        if alias is None:
            self._list_root_html()
        else:
            self._handle_get(alias, remote_path)

    def do_HEAD(self):
        if not self._require_auth():
            return
        alias, remote_path = self._parse_path()
        if alias is None:
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            sftp, conn = self._get_sftp(alias)
            if not sftp:
                self._safe_send_error(404)
                return
            try:
                stat_info = sftp.stat(remote_path)
                self.send_response(200)
                is_dir = stat_info.st_mode is not None and stat_info.st_mode & 0o40000
                self.send_header("Content-Type", "httpd/unix-directory" if is_dir else "application/octet-stream")
                self.send_header("Content-Length", "0" if is_dir else str(stat_info.st_size or 0))
                self.send_header("Last-Modified", self._format_time(stat_info.st_mtime or time.time()))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
            except FileNotFoundError:
                self._safe_send_error(404)
            except Exception as e:
                logger.error("HEAD error: %s", e)
                self._safe_send_error(500)
            finally:
                self._close_sftp(sftp)
                self._release(conn)

    def do_PUT(self):
        if not self._require_auth():
            return
        alias, remote_path = self._parse_path()
        if alias is None:
            self._drain_request_body()
            self._safe_send_error(400, "Account alias required")
        else:
            self._handle_put(alias, remote_path)

    def do_DELETE(self):
        self._drain_request_body()
        if not self._require_auth():
            return
        alias, remote_path = self._parse_path()
        if alias is None:
            self._safe_send_error(400, "Account alias required")
        else:
            self._handle_delete(alias, remote_path)

    def do_MKCOL(self):
        self._drain_request_body()
        if not self._require_auth():
            return
        alias, remote_path = self._parse_path()
        if alias is None:
            self._safe_send_error(400, "Account alias required")
        else:
            self._handle_mkcol(alias, remote_path)

    def do_MOVE(self):
        self._drain_request_body()
        if not self._require_auth():
            return
        alias, remote_path = self._parse_path()
        if alias is None:
            self._safe_send_error(400, "Account alias required")
        else:
            self._handle_move(alias, remote_path)

    def do_COPY(self):
        self._drain_request_body()
        if not self._require_auth():
            return
        alias, remote_path = self._parse_path()
        if alias is None:
            self._safe_send_error(400, "Account alias required")
        else:
            self._handle_copy(alias, remote_path)

    def do_LOCK(self):
        self._drain_request_body()
        if not self._require_auth():
            return
        token = f"opaquelocktoken:{uuid.uuid4()}"
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<D:prop xmlns:D="DAV:">
  <D:lockdiscovery>
    <D:activelock>
      <D:locktype><D:write/></D:locktype>
      <D:lockscope><D:exclusive/></D:lockscope>
      <D:depth>{_xml_escape(self.headers.get("Depth", "infinity"))}</D:depth>
      <D:owner>OpsV-Kits</D:owner>
      <D:timeout>Second-600</D:timeout>
      <D:locktoken><D:href>{token}</D:href></D:locktoken>
    </D:activelock>
  </D:lockdiscovery>
</D:prop>"""
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Lock-Token", f"<{token}>")
        self.end_headers()
        self.wfile.write(encoded)

    def do_UNLOCK(self):
        self._drain_request_body()
        if not self._require_auth():
            return
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

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
    )


class RemoteDriveService:
    def __init__(self):
        self._server: Optional[_SilentThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, host: str = "0.0.0.0", port: int = 8081) -> bool:
        with self._lock:
            if self._running:
                return True
            try:
                _WebDAVRequestHandler.SSH_SERVICE = ssh_account_service
                self._server = _SilentThreadingHTTPServer((host, port), _WebDAVRequestHandler)
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

    def restart(self, host: str = "0.0.0.0", port: int = 8081) -> bool:
        self.stop()
        time.sleep(0.5)
        return self.start(host, port)


remote_drive_service = RemoteDriveService()
