from SSSL.server import Server


# This class makes the Server object accessible from anywhere
class ServerApp:
    server = None

    @staticmethod
    def get_server():
        if ServerApp.server is None:
            ServerApp.server = Server('app/server-04.pem', 'app/server_prvkey.key')
            ServerApp.server.start()
        return ServerApp.server
