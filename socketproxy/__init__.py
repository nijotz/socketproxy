import errno
import logging
import select
import socket
from socket import error as SocketError
try:
    import socketserver
except ImportError:
    import SocketServer as socketserver


class SocketProxyRequestHandler(socketserver.BaseRequestHandler):
    "New instances are created for each connection"

    def setup(self):
        "Connects to the upstream server"
        # pulls upstream connection information from the server class
        self.upstream = self.server.upstream
        self.upstream_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.upstream_conn.connect(self.upstream)

    def proxy_data(self, sender, receiver):
        "Attempts to proxy data, returning whether or not connection was open"

        data = sender.recv(4096)

        if data:
            # Received data, send it through
            receiver.sendall(data)
            return True
        else:
            # No data, other side closed connection
            return False

    def handle(self):

        errors = False    # there were connection errors
        readables = True  # there are readable connections (vs timeout)
        closed = False    # the connection was closed

        while not errors and not closed and readables:

            # Wait for one of the sockets to become readable or closed
            sockets = (self.request, self.upstream_conn)
            readables, _, errors = select.select(sockets, (), sockets, 30)

            try:
                for readable in readables:
                    # Upstream is sending to client
                    if readable is self.upstream_conn:
                        args = (self.upstream_conn, self.request)
                    # Client is sending to upstream
                    else:
                        args = (self.request, self.upstream_conn)
                    closed = not self.proxy_data(*args)

            # Catch sockets closing and ignore them
            except SocketError as e:
                if e.errno != errno.ECONNRESET and e.errno != errno.EPIPE:
                    raise


class SocketProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    def __init__(self, upstream_host, upstream_port, server_host='localhost',
                 server_port='8080', handler_class=SocketProxyRequestHandler):

        # False for bind_and_activate will skip the socket bind on init so
        # that allow_reuse_address can be set on the socket which will call
        # socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) which avoids 'Address
        # is already in use' errors when/if the server crashes non-gracefully
        socketserver.TCPServer.__init__(self, (server_host, int(server_port)),
                                        handler_class, bind_and_activate=False)

        self.allow_reuse_address = True
        # The above sets SO_REUSEADDR, but on OSX I needed REUSEPORT too
        if getattr(socket, 'SO_REUSEPORT', None):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.server_bind()
        self.server_activate()

        self.upstream = (upstream_host, int(upstream_port))


class PlumbingRequestHandler(SocketProxyRequestHandler):

    def proxy_data(self, sender, receiver):
        data = sender.recv(4096)

        if data:
            if sender is self.upstream_conn:
                method = "to_client"
            else:
                method = "to_upstream"

            for pipe in self.server.pipes:
                data = getattr(pipe, method)(data)

            receiver.sendall(data)
            return True
        else:
            return False


class PlumbingServer(SocketProxyServer):
    "Now with pipes!"

    def __init__(self, *args, **kwargs):
        SocketProxyServer.__init__(
            self, *args, handler_class=PlumbingRequestHandler, **kwargs)
        self.pipes = []

    def add_pipe(self, pipe):
        self.pipes.append(pipe)


class Pipe(object):
    "Can be hooked up to a PlumbingServer"

    def to_client(self, data):
        return data

    def to_upstream(self, data):
        return data


def main(proxy_class):

    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Proxy a socket connection')
    parser.add_argument('host')
    parser.add_argument('port')
    args = parser.parse_args()

    # Setup logging to stdout
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    # Start proxy
    logging.info(
        'Starting proxy to connect to {} on port {}'.format(
            args.host, args.port))
    proxy = proxy_class(args.host, args.port)
    proxy.serve_forever()

if __name__ == '__main__':
    main(SocketProxyServer)
