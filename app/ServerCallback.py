from SSSL import util
from app.models import *
from django.utils import timezone
from app.Clients import Clients
import threading

class ServerCallback:

    ids = dict()
    show_reply_id = 0

    callback_lock = threading.Lock()
    
    @staticmethod
    def callback(payload, user_id):
        if len(payload) < 1:
            print 'todo err'
            return
        if payload[0] == ord('\x01'):
            message_id = ServerCallback.parse_message(payload, user_id)
            if message_id:
                return ServerCallback.create_ack(message_id)
            else:
                return

        if payload[0] == ord('\x03'):
            messages = ServerCallback.parse_show(payload, user_id)
            if messages:
                return ServerCallback.create_show_reply(messages)
            else:
                return

    @staticmethod
    def callback_client(payload, client):
        if len(payload) < 1:
            print 'todo err'
            return
        if payload[0] == ord('\x04'):
            ServerCallback.parse_ack(payload, client)

        print "RECEIVED REPLY"
        if payload[0] == ord('\x05') or payload[0] == ord('\x06'):
            ServerCallback.callback_lock.acquire()
            print "haslock"
            ServerCallback.parse_show_reply(payload, client)
            ServerCallback.callback_lock.release()
            print "releasedlock"


    @staticmethod
    def create_message(message, conn):
        length = len(message)
        server_hello = bytearray((6+length) * '\x00', 'hex')
        server_hello[0] = '\x01' #message

        message_id = ServerCallback.ids.get(conn)
        if not message_id:
            message_id = 0
        else:
            message_id += 1
            message_id %= 256
        ServerCallback.ids[conn] = message_id

        server_hello[1:2] = util.int_to_binary(message_id, 1)

        message_binary = util.text_to_binary(message)

        server_hello[2:4] = util.int_to_binary(length, 2)
        server_hello[4:4+length] = message_binary

        server_hello[4+length:6+length] = '\xF0\xF0'
        return server_hello

    @staticmethod
    def create_show( conn):
        server_hello = bytearray((3) * '\x00', 'hex')
        server_hello[0] = '\x03' #show

        server_hello[1:3] = '\xF0\xF0'
        return server_hello



    @staticmethod
    def parse_message(payload, user_id):
        message_id = payload[1:2]
        length = util.binary_to_int(payload[2:4])
        message = util.binary_to_text(payload[4:4+length])
        print "Server received", message

        if not (payload[4+length] == ord('\xF0') and payload[5+length] == ord('\xF0')) :
            print 'todo err' #todo reset conn
            return
        user_db = User.objects.get(user_id=user_id)
        message_db = Message(user_id=user_db, date=timezone.now(), text=message)
        message_db.save() #to database
        return message_id

    @staticmethod
    def parse_show(payload, user_id):
        if not (payload[1] == ord('\xF0') and payload[2] == ord('\xF0')) :
            print 'todo err' #todo reset conn
            return
        messages = Message.objects.all().order_by('-date') # - means desc

        return messages
        

    @staticmethod
    def create_ack(message_id):
        server_hello = bytearray((2) * '\x00', 'hex')
        server_hello[0] = '\x04' #message


        server_hello[1:2] = message_id

        return [server_hello]

    @staticmethod
    def create_show_reply(messages):
        payloads = []
        show_reply_initial = bytearray((6) * '\x00', 'hex')
        show_reply_initial[0] = '\x05' #show reply
        reply_id = ServerCallback.show_reply_id
        ServerCallback.show_reply_id += 1
        ServerCallback.show_reply_id %=256
        show_reply_initial[1:2] = util.int_to_binary(reply_id, 1)
        show_reply_initial[2:4] = util.int_to_binary(len(messages), 2)
        show_reply_initial[4:6] = '\xF0\xF0'
        payloads.append(show_reply_initial)

        for message in messages:
            message_bytes = util.text_to_binary(message.text)
            length = len(message_bytes)
            show_reply_message = bytearray((6+length) * '\x00', 'hex')
            show_reply_message[0] = '\x06'  # show reply message
            show_reply_message[1:2] = util.int_to_binary(reply_id, 1)
            show_reply_message[2:4] = util.int_to_binary(length, 2)
            show_reply_message[4:4+length] = message_bytes
            show_reply_message[4+length:6+length] = '\xF0\xF0'
            payloads.append(show_reply_message)

        return payloads


    @staticmethod
    def parse_ack(payload, client):

        message_id = util.binary_to_int(payload[1:2])
        print "PARSING ACK", message_id, Clients.client_to_session_key[client]
        Clients.acks[Clients.client_to_session_key[client]] = message_id


    @staticmethod
    def parse_show_reply(payload, client):

        session_key = Clients.client_to_session_key[client]
        if payload[0] ==  ord('\x05'):  # show reply
            Clients.show_ids[session_key] = util.binary_to_int(payload[1:2])
            Clients.show_data[session_key] = []
            Clients.show_lengths[session_key] = util.binary_to_int(payload[2:4])

        elif payload[0] ==  ord('\x06'):  # show reply message
            if Clients.show_ids.get(session_key) != util.binary_to_int(payload[1:2]):
                #outdated, ignore
                return

            length = util.binary_to_int(payload[2:4])

            message_bytes = payload[4:4 + length]

            Clients.show_data.get(session_key).append(util.binary_to_text(message_bytes))
            print "ADDED"
