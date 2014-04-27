import logging
import select
import socket
import SocketServer


class SocketProxyRequestHandler(SocketServer.BaseRequestHandler):
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
        errors = False
        readables = True
        closed = False
        while not errors and not closed and readables:
            # Wait for one of the sockets to become readable or closed
            sockets = (self.request, self.upstream_conn)
            readables, _, errors = select.select(sockets, (), sockets, 3)

            for readable in readables:
                if readable is self.upstream_conn:
                    if not self.proxy_data(self.upstream_conn, self.request):
                        closed = True
                else:
                    if not self.proxy_data(self.request, self.upstream_conn):
                        closed = True


class SocketProxyServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

    def __init__(self, upstream_host, upstream_port, server_host='localhost',
                 server_port='8080', handler_class=SocketProxyRequestHandler):

        # False is for bind_and_activate, which will skip the socket bind on
        # init so that allow_reuse_address can be set on the socket which will
        # call socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) which avoids
        # 'Address is already in use' errors when server crashes non-gracefully
        SocketServer.TCPServer.__init__(self, (server_host, int(server_port)),
                                        handler_class, bind_and_activate=False)

        self.allow_reuse_address = True
        # The above sets SO_REUSEADDR, but on OSX I needed REUSEPORT too
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
                receiver.sendall(getattr(pipe, method)(data))
            return True
        else:
            return False


class PlumbingServer(SocketProxyServer):
    "Now with pipes!"

    def __init__(self, *args, **kwargs):
        SocketProxyServer.__init__(self, *args, handler_class=PlumbingRequestHandler, **kwargs)
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
