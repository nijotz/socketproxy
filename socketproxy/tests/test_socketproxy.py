import os
import socket
import threading
import unittest
from socketproxy import Pipe, SocketProxyServer, PlumbingServer


class TestProxy(unittest.TestCase):

    def testBasicConnect(self):
        # Start proxy
        proxy = SocketProxyServer('google.com', '80', 'localhost', '8080')
        proxy_thread = threading.Thread(target=proxy.serve_forever)
        proxy_thread.daemon = True
        proxy_thread.start()

        try:
            # Connect to the proxy
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 8080))
            sock.sendall('GET /index.html\r\n')
            data = sock.recv(1024)
            sock.close()
        finally:
            # Stop proxy
            proxy.shutdown()

        self.assertNotEqual(data, '')

    def testPipeProxy(self):

        class OhToZero(Pipe):
            def to_client(self, data):
                data = data.replace('o', '0')
                data = data.replace('O', '0')
                return data

        # Start proxy with pipe
        proxy = PlumbingServer('google.com', '80', 'localhost', '8080')
        proxy.add_pipe(OhToZero())
        proxy_thread = threading.Thread(target=proxy.serve_forever)
        proxy_thread.daemon = True
        proxy_thread.start()

        try:
            # Connect to the proxy
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 8080))
            sock.sendall('GET /index.html\r\n')
            data = sock.recv(1024)
            sock.close()
        finally:
            # Stop proxy
            proxy.shutdown()

        self.assertTrue(data.find('g00gle') != -1)


class TestCodeFormat(unittest.TestCase):

    def test_pep8_compliance(self):
        import pep8
        pep8test = pep8.StyleGuide(quiet=True, reporter=pep8.StandardReport)
        result = pep8test.check_files([
            'socketproxy/tests/test_socketproxy.py',
            'socketproxy/__init__.py',
            ])
        self.assertEqual(result.total_errors, 0)

    def test_pyflakes_compliance(self):
        from pyflakes import reporter
        from pyflakes import api

        class PyflakesReporter(reporter.Reporter):
            def __init__(self, *args, **kwargs):
                self.error = False

            def unexpectedError(self, *args, **kwargs):
                self.error = True

            def syntaxError(self, *args, **kwargs):
                self.error = True

            def flake(self, *args, **kwargs):
                self.error = True

        path = os.path.dirname(os.path.realpath(__file__))

        reporter = PyflakesReporter()
        api.checkRecursive([path], reporter)
        self.assertEqual(reporter.error, False)
