from SSSL import util
from app.Clients import Clients


class ClientCallback:
    ids = dict()

    @staticmethod
    def callback(payload, client):
        if len(payload) < 1:
            return
        # Choose how to parse depending on first byte
        if payload[0] == ord('\x04'):
            ClientCallback.parse_ack(payload, client)

        if payload[0] == ord('\x05') or payload[0] == ord('\x06') or payload[0] == ord('\x07'):
            ClientCallback.parse_show_reply(payload, client)


    @staticmethod
    def create_message(message, conn):
        length = len(message)
        packet = bytearray((8+length) * '\x00', 'hex')
        packet[0] = '\x01' # message

        # Get next available message ID
        message_id = ClientCallback.ids.get(conn)
        if not message_id:
            message_id = 0
        else:
            message_id += 1
            message_id %= 256
            ClientCallback.ids[conn] = message_id

        packet[1:2] = util.int_to_binary(message_id, 1)

        message_binary = util.text_to_binary(message)

        packet[2:6] = util.int_to_binary(length, 4)
        packet[6:6+length] = message_binary

        packet[6+length:8+length] = '\xF0\xF0'
        print "Sent message payload"
        return packet

    @staticmethod
    def create_show( conn):
        show_message = bytearray(3 * '\x00', 'hex')
        show_message[0] = '\x03' # show

        show_message[1:3] = '\xF0\xF0'
        print "Sent show payload"
        return show_message


    @staticmethod
    def create_image(image, conn):
        name = image.name
        name_binary = util.text_to_binary(name)
        name_length = len(name_binary)

        image_contents = image.read()
        image_binary = util.text_to_binary(image_contents)
        length = len(image_binary)
        client_image = bytearray((9+length+name_length) * '\x00', 'hex')
        client_image[0] = '\x02' # image

        image_id = ClientCallback.ids.get(conn)
        if not image_id:
            image_id = 0
        else:
            image_id += 1
            image_id %= 256
            ClientCallback.ids[conn] = image_id

        client_image[1:2] = util.int_to_binary(image_id, 1)

        client_image[2:3] = util.int_to_binary(name_length, 1)
        client_image[3:3+name_length] = name_binary

        client_image[3+name_length:7+name_length] = util.int_to_binary(length, 4)
        client_image[7+name_length:7+name_length+length] = image_binary

        client_image[7+name_length+length:9+name_length+length] = '\xF0\xF0'
        print "Sent image payload"
        return client_image


    @staticmethod
    def parse_ack(payload, client):
        print "Received ack payload"
        # Mark that ack was received for this message ID
        message_id = util.binary_to_int(payload[1:2])
        Clients.acks[Clients.client_to_session_key[client]] = message_id


    @staticmethod
    def parse_show_reply(payload, client):

        session_key = Clients.client_to_session_key[client]
        if payload[0] ==  ord('\x05'):  # show reply
            print "Received initial show data reply payload"
            # Mark receive started for this ID, mark how many items are expected
            Clients.show_ids[session_key] = util.binary_to_int(payload[1:2])
            Clients.show_data[session_key] = []
            Clients.show_lengths[session_key] = util.binary_to_int(payload[2:4])

        elif payload[0] ==  ord('\x06'):  # show reply message
            if Clients.show_ids.get(session_key) != util.binary_to_int(payload[1:2]):
                #outdated, ignore
                return
            # Extract the message
            length = util.binary_to_int(payload[2:6])
            message_bytes = payload[6:6 + length]
            Clients.show_data.get(session_key).append(['text', util.binary_to_text(message_bytes)])

        elif payload[0] == ord('\x07'):  # show reply image
            if Clients.show_ids.get(session_key) != util.binary_to_int(payload[1:2]):
                # outdated, ignore
                return

            # Extract the binary image, HTML will convert to actual image
            length = util.binary_to_int(payload[2:6])
            image_bytes = payload[6:6 + length]
            Clients.show_data.get(session_key).append(['image', util.binary_to_text(image_bytes)])
