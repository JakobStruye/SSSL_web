from SSSL.server import Server

class ServerApp:
    server = None
    @staticmethod
    def get_server():
        if ServerApp.server is None:
            print "isnone"
            ServerApp.server = Server('app/server-04.pem', 'app/server_prvkey.key')
            ServerApp.server.start()
        return ServerApp.server
