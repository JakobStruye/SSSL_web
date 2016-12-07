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
            image_id = ServerCallback.parse_message(payload, user_id)
            if image_id:
                return ServerCallback.create_ack(image_id)
            else:
                return

        if payload[0] == ord('\x02'):
            image_id = ServerCallback.parse_image(payload, user_id)
            if image_id:
                return ServerCallback.create_ack(image_id)
            else:
                return

        if payload[0] == ord('\x03'):
            messages, images = ServerCallback.parse_show(payload, user_id)
            if messages or images:
                return ServerCallback.create_show_reply(messages, images)
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
        if payload[0] == ord('\x05') or payload[0] == ord('\x06') or payload[0] == ord('\x07'):
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
    def create_image(image, conn):
        name = image.name
        name_binary = util.text_to_binary(name)
        name_length = len(name_binary)
        image_contents = image.read()
        image_binary = util.text_to_binary(image_contents)
        length = len(image_binary)
        client_image = bytearray((7+length+name_length) * '\x00', 'hex')
        client_image[0] = '\x02' #image

        image_id = ServerCallback.ids.get(conn)
        if not image_id:
            image_id = 0
        else:
            image_id += 1
            image_id %= 256
        ServerCallback.ids[conn] = image_id

        client_image[1:2] = util.int_to_binary(image_id, 1)

        client_image[2:3] = util.int_to_binary(name_length, 1)
        client_image[3:3+name_length] = name_binary

        client_image[3+name_length:5+name_length] = util.int_to_binary(length, 2)
        client_image[5+name_length:5+name_length+length] = image_binary

        client_image[5+name_length+length:7+name_length+length] = '\xF0\xF0'
        return client_image



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
    def parse_image(payload, user_id):


        image_id = payload[1:2]

        name_length = util.binary_to_int(payload[2:3])
        name = util.binary_to_text(payload[3:3+name_length])
        length = util.binary_to_int(payload[3+name_length:5+name_length])
        image = util.binary_to_text(payload[5+name_length:5+name_length+length])

        newFile = open("images/"+name, "wb")

        newFile.write(image)

        if not (payload[5+name_length+length] == ord('\xF0') and payload[6+name_length+length] == ord('\xF0')) :
            print 'todo err' #todo reset conn
            return

        user_db = User.objects.get(user_id=user_id)
        image_db = Image(user_id=user_db, date=timezone.now(), image_location="images/"+name)
        image_db.save() #to database
        return image_id

    @staticmethod
    def parse_show(payload, user_id):
        if not (payload[1] == ord('\xF0') and payload[2] == ord('\xF0')) :
            print 'todo err' #todo reset conn
            return
        messages = Message.objects.all().order_by('-date') # - means desc
        images = Image.objects.all().order_by('-date') # - means desc


        return messages, images
        

    @staticmethod
    def create_ack(message_id):
        server_hello = bytearray((2) * '\x00', 'hex')
        server_hello[0] = '\x04' #message


        server_hello[1:2] = message_id

        return [server_hello]

    @staticmethod
    def create_show_reply(messages, images):
        payloads = []
        show_reply_initial = bytearray((6) * '\x00', 'hex')
        show_reply_initial[0] = '\x05' #show reply
        reply_id = ServerCallback.show_reply_id
        ServerCallback.show_reply_id += 1
        ServerCallback.show_reply_id %=256
        show_reply_initial[1:2] = util.int_to_binary(reply_id, 1)
        show_reply_initial[2:4] = util.int_to_binary(len(messages)+len(images), 2)
        show_reply_initial[4:6] = '\xF0\xF0'
        payloads.append(show_reply_initial)

        message_it = iter(messages)
        image_it = iter(images)

        try:
            message = message_it.next()
        except StopIteration:
            message = None

        try:
            image = image_it.next()
        except StopIteration:
            image = None

        while message is not None or image is not None:
            if image is None and message is not None or image.date < message.date:
                payload = ServerCallback.create_show_reply_message(message, reply_id)
                try:
                    message = message_it.next()
                except StopIteration:
                    message = None
            elif message is None or message.date < image.date:
                payload = ServerCallback.create_show_reply_image(image, reply_id)
                try:
                    image = image_it.next()
                except StopIteration:
                    image = None
            payloads.append(payload)


        return payloads

    @staticmethod
    def create_show_reply_message(message, reply_id):
        message_bytes = util.text_to_binary(message.text)
        length = len(message_bytes)
        show_reply_message = bytearray((6 + length) * '\x00', 'hex')
        show_reply_message[0] = '\x06'  # show reply message
        show_reply_message[1:2] = util.int_to_binary(reply_id, 1)
        show_reply_message[2:4] = util.int_to_binary(length, 2)
        show_reply_message[4:4 + length] = message_bytes
        show_reply_message[4 + length:6 + length] = '\xF0\xF0'
        return show_reply_message


    @staticmethod
    def create_show_reply_image(image, reply_id):
        newFile = open(image.image_location, "rb")

        image_bytes = util.text_to_binary(newFile.read())
        length = len(image_bytes)
        show_reply_image = bytearray((6 + length) * '\x00', 'hex')
        show_reply_image[0] = '\x07'  # show reply image
        show_reply_image[1:2] = util.int_to_binary(reply_id, 1)
        show_reply_image[2:4] = util.int_to_binary(length, 2)
        show_reply_image[4:4 + length] = image_bytes
        show_reply_image[4 + length:6 + length] = '\xF0\xF0'
        return show_reply_image


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

            Clients.show_data.get(session_key).append(['text', util.binary_to_text(message_bytes)])
            print "ADDED"

        elif payload[0] == ord('\x07'):  # show reply image
            if Clients.show_ids.get(session_key) != util.binary_to_int(payload[1:2]):
                # outdated, ignore
                return

            length = util.binary_to_int(payload[2:4])

            image_bytes = payload[4:4 + length]

            Clients.show_data.get(session_key).append(['image', util.binary_to_text(image_bytes)])
            print "ADDED"
