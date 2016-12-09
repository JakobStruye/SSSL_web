from SSSL import util
from app.models import *
from django.utils import timezone



class ServerCallback:

    show_reply_id = 0

    @staticmethod
    def callback(payload, user_id):
        if len(payload) < 1:
            return # ignore
        # Choose how to parse depending on first byte
        if payload[0] == ord('\x01'):
            message_id = ServerCallback.parse_message(payload, user_id)
            if message_id:
                return ServerCallback.create_ack(message_id)
            else:
                return

        elif payload[0] == ord('\x02'):
            image_id = ServerCallback.parse_image(payload, user_id)
            if image_id:
                return ServerCallback.create_ack(image_id)
            else:
                return

        elif payload[0] == ord('\x03'):
            messages, images = ServerCallback.parse_show(payload, user_id)
            if messages or images:
                return ServerCallback.create_show_reply(messages, images)
            else:
                return



    @staticmethod
    def parse_message(payload, user_id):
        print "Received message payload"
        message_id = payload[1:2]
        length = util.binary_to_int(payload[2:6])
        message = util.binary_to_text(payload[6:6+length])

        if not (payload[6+length] == ord('\xF0') and payload[7+length] == ord('\xF0')):
            # Invalid, ignore
            return
        user_db = User.objects.get(user_id=user_id)
        message_db = Message(user_id=user_db, date=timezone.now(), text=message)
        message_db.save()  # to database

        return message_id


    @staticmethod
    def parse_image(payload, user_id):
        print "Received image payload"
        image_id = payload[1:2]

        name_length = util.binary_to_int(payload[2:3])
        name = util.binary_to_text(payload[3:3+name_length])
        length = util.binary_to_int(payload[3+name_length:7+name_length])
        image = util.binary_to_text(payload[7+name_length:7+name_length+length])

        # Save image to file using provided name
        new_file = open("images/" + name, "wb")

        new_file.write(image)

        if not (payload[7+name_length+length] == ord('\xF0') and payload[8+name_length+length] == ord('\xF0')) :
            # Invalid, ignore
            return

        user_db = User.objects.get(user_id=user_id)
        image_db = Image(user_id=user_db, date=timezone.now(), image_location="images/"+name)
        image_db.save() #to database

        return image_id

    @staticmethod
    def parse_show(payload, user_id):
        print "Received show data payload"
        if not (payload[1] == ord('\xF0') and payload[2] == ord('\xF0')) :
            # Invalid, ignore
            return

        # Get the messages and images to send to client
        messages = Message.objects.all().order_by('-date') # - means desc
        images = Image.objects.all().order_by('-date') # - means desc

        return messages, images

    @staticmethod
    def create_ack(message_id):
        server_hello = bytearray(2 * '\x00', 'hex')
        server_hello[0] = '\x04' # ack

        server_hello[1:2] = message_id
        print "Sent ack payload"
        return [server_hello]

    @staticmethod
    def create_show_reply(messages, images):
        payloads = []
        show_reply_initial = bytearray((6) * '\x00', 'hex')
        show_reply_initial[0] = '\x05' # show reply
        # initial packet indicating how many items will be sent, and each item are all sent in separate packets
        # reply_id indicates they belong together
        reply_id = ServerCallback.show_reply_id
        ServerCallback.show_reply_id += 1
        ServerCallback.show_reply_id %= 256
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
            # From most to least recent, mix messages and images
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
        print "Sent", len(payloads), "show data payloads"
        return payloads

    @staticmethod
    def create_show_reply_message(message, reply_id):
        message_bytes = util.text_to_binary(message.text)
        length = len(message_bytes)
        show_reply_message = bytearray((8 + length) * '\x00', 'hex')
        show_reply_message[0] = '\x06'  # show reply message
        show_reply_message[1:2] = util.int_to_binary(reply_id, 1)
        show_reply_message[2:6] = util.int_to_binary(length, 4)
        show_reply_message[6:6 + length] = message_bytes
        show_reply_message[6 + length:8 + length] = '\xF0\xF0'
        return show_reply_message


    @staticmethod
    def create_show_reply_image(image, reply_id):
        # Back from file to bytes
        newFile = open(image.image_location, "rb")

        image_bytes = util.text_to_binary(newFile.read())
        length = len(image_bytes)
        show_reply_image = bytearray((8 + length) * '\x00', 'hex')
        show_reply_image[0] = '\x07'  # show reply image
        show_reply_image[1:2] = util.int_to_binary(reply_id, 1)
        show_reply_image[2:6] = util.int_to_binary(length, 4)
        show_reply_image[6:6 + length] = image_bytes
        show_reply_image[6 + length:8 + length] = '\xF0\xF0'
        return show_reply_image
