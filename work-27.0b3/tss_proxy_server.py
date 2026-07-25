#!/usr/bin/env python3.14

from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request

TSS_URL = 'https://gs.apple.com/TSS/controller?action=2'

# eUICC keys to inject into the root dict of the original request on STATUS=168
EUICC_KEYS = (
    "\t<key>eUICC,ApProductionMode</key>\n"
    "\t<true/>\n"
    "\t<key>eUICC,ChipID</key>\n"
    "\t<integer>5</integer>\n"
    "\t<key>eUICC,EID</key>\n"
    "\t<data>\n"
    "\tiQSQMgBQCIgmAASEJAh2MQ==\n"
    "\t</data>\n"
    "\t<key>eUICC,RootKeyIdentifier</key>\n"
    "\t<data>\n"
    "\tQVhK/T5EfBDbGEdwMfU42u7Qx9M=\n"
    "\t</data>\n"
)


class SimpleHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        # 1. Read the request body
        post_data = b""
        if content_length > 0:
            post_data = self.rfile.read(content_length)

            # 2. Decode to text and print (optional)
            print("--- Received POST Data ---")
            print(post_data.decode('utf-8', errors='replace'))
            print("--------------------------")

        if self.path == '/TSS/controller?action=2':
            try:
                # 3. Forward the original request as-is to gs.apple.com
                response_data = self._forward_to_tss(post_data)
                print("--- TSS Response ---")
                print(response_data.decode('utf-8', errors='replace'))
                print("--------------------")

                # 4. Only on STATUS=168, inject eUICC keys and resend
                if self._tss_status(response_data) == '168':
                    print("[!] STATUS=168 detected -> injecting eUICC keys and retrying")
                    modified = self._inject_euicc(post_data)

                    print("--- Retried Request (with eUICC) ---")
                    print(modified.decode('utf-8', errors='replace'))
                    print("------------------------------------")

                    response_data = self._forward_to_tss(modified)

                    print("--- Retried TSS Response ---")
                    print(response_data.decode('utf-8', errors='replace'))
                    print("----------------------------")

                # 5. Return the final response
                self.send_response(200)
                self.end_headers()
                self.wfile.write(response_data)
            except Exception as e:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        self.do_POST()

    @staticmethod
    def _forward_to_tss(post_data):
        """Forward post_data to the real TSS server and return the response bytes."""
        req = urllib.request.Request(
            TSS_URL,
            data=post_data,
            headers={
                'Content-Type': 'text/xml; charset="utf-8"',
                'User-Agent': 'InetURL/1.0',
                'Cache-Control': 'no-cache',
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()

    @staticmethod
    def _tss_status(response_data):
        """Extract the STATUS value from a TSS response (e.g. 'STATUS=168&MESSAGE=...' -> '168')."""
        text = response_data.decode('utf-8', errors='replace')
        # STATUS is always the first '&'-delimited field, so only inspect the head
        first = text.split('&', 1)[0]
        if first.startswith('STATUS='):
            return first[len('STATUS='):].strip()
        return None

    @staticmethod
    def _inject_euicc(post_data):
        """Insert the eUICC keys just before the root </dict> of the original plist request."""
        text = post_data.decode('utf-8', errors='replace')

        # Avoid double injection if the keys are already present
        if 'eUICC,ChipID' in text:
            return post_data

        # The root dict's closing tag is the last </dict> in the document
        idx = text.rfind('</dict>')
        if idx == -1:
            return post_data  # Not a plist structure; return unchanged

        return (text[:idx] + EUICC_KEYS + text[idx:]).encode('utf-8')


if __name__ == '__main__':
    print("Server running on http://127.0.0.1:1337 ...")
    HTTPServer(('127.0.0.1', 1337), SimpleHandler).serve_forever()