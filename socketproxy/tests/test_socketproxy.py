from __future__ import print_function
import socket
import threading
import unittest
from socketproxy import Pipe, SocketProxyServer, PlumbingServer


class TestProxy(unittest.TestCase):

    def start_proxy(self, proxy_cls=SocketProxyServer):
        "Used by the following tests to setup a server and connect to it"
        # Start proxy
        proxy = proxy_cls('google.com', '80', 'localhost', '8080')
        proxy_thread = threading.Thread(target=proxy.serve_forever)
        proxy_thread.daemon = True
        proxy_thread.start()
        return proxy

    def connect_to_proxy(self, proxy):
        try:
            # Connect to the proxy
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 8080))
            sock.sendall(b'GET /index.html\r\n')
            data = sock.recv(1024)
            sock.close()
        finally:
            # Stop proxy
            proxy.shutdown()

        return data

    def testBasicConnect(self):
        proxy = self.start_proxy()
        data = self.connect_to_proxy(proxy)
        self.assertNotEqual(data, '')

    def testPipeProxy(self):

        class OhToZero(Pipe):
            def to_client(self, data):
                data = data.replace(b'o', b'0')
                data = data.replace(b'O', b'0')
                return data

        proxy = self.start_proxy(PlumbingServer)
        proxy.add_pipe(OhToZero())
        data = self.connect_to_proxy(proxy)
        self.assertTrue(data.find(b'g00gle') != -1)


class TestCodeFormat(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestCodeFormat, self).__init__(*args, **kwargs)
        self.path = ['socketproxy']

    def test_pep8_compliance(self):
        import pep8

        # Using the StandardReport will give you filenames and linenumbers
        pep8test = pep8.StyleGuide(quiet=True, reporter=pep8.StandardReport)
        result = pep8test.check_files(self.path)
        self.assertEqual(result.total_errors, 0)

    def test_pyflakes_compliance(self):
        from pyflakes import reporter
        from pyflakes import api

        class PyflakesReporter(reporter.Reporter):
            def print_error(self, error):
                message = error.message % error.message_args
                print("{filename}: {message}".format(
                    filename=error.filename,
                    message=message,
                ))

            def __init__(self, *args, **kwargs):
                self.error = False

            def unexpectedError(self, *args, **kwargs):
                arg = args[0]
                self.print_error(arg)
                self.error = True

            def syntaxError(self, *args, **kwargs):
                arg = args[0]
                self.print_error(arg)
                self.error = True

            def flake(self, *args, **kwargs):
                arg = args[0]
                self.print_error(arg)
                self.error = True

        reporter = PyflakesReporter()
        api.checkRecursive(self.path, reporter)
        self.assertEqual(reporter.error, False)
