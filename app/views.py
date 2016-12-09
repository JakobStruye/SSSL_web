from django.http import HttpResponse
from django.shortcuts import render
from SSSL.client import Client
from Clients import Clients
from ServerApp import ServerApp
from ClientCallback import ClientCallback
import time
from django import forms
import base64


def index(request):
    # Get server object, initiate some variables
    ServerApp.get_server()
    if not request.session.get('has_session'):  # Force setting session key
        request.session['has_session'] = True
    has_connection = (Clients.clients.get(request.session.session_key) is not None)
    context = {'has_connection': has_connection}
    if not has_connection and request.POST.get('connect'):
        print "User input: connect"
        # User clicked the connect button, set up connection
        client = Client('client-05.pem', 'project-client', 'Konklave123')
        client.add_payload_listener(ClientCallback)
        error = client.connect('localhost', 8970)  # Replace with IP address to connect to non-local server

        if error == 0:
            Clients.clients[request.session.session_key] = client
            context['has_connection'] = True
        else:
            context['has_connection'] = False
            context['has_error'] = True

    # Extract some values from static objects
    if request.session.session_key:
        conn = Clients.clients.get(request.session.session_key)
        Clients.client_to_session_key[conn] = request.session.session_key

    if has_connection and request.POST.get('disconnect'):
        # User clicked disconnect button, close connection
        print "User input: disconnect"

        conn.disconnect()
        Clients.clients[request.session.session_key] = None
        context['has_connection'] = False

    if has_connection and request.POST.get('message'):
        # User clicked message button, send to server
        print "User input: send message"
        if request.POST.get('messagetext') == "":
            return render(request, 'app/index.html', context)  # Nothing filled in, ignore

        message = ClientCallback.create_message(request.POST.get('messagetext'), conn)
        try:
            conn.send_payload(message)
        except:
            context['connection_lost'] = True  # Connection may have been closed
        context['needs_ack'] = True
        has_ack = False
        # For 10 seconds, check if ack came in once per 100ms. Continue on receive or timeout.
        for i in range(100):
            if Clients.acks.get(request.session.session_key) == message[1]:
                has_ack = True
                break
            time.sleep(0.1)
        context['has_ack'] = has_ack

    if has_connection and request.POST.get('show'):
        print "User input: show data"
        # User clicked show button, request all items from server
        Clients.show_ids[request.session.session_key] = None
        message = ClientCallback.create_show(conn)
        try:
            conn.send_payload(message)
        except:
            context['connection_lost'] = True

        context['needs_show'] = True
        has_show = False
        # Allow 10 seconds to receive all data.
        for i in range(100):
            if Clients.show_ids.get(request.session.session_key) is not None:  # First reply received
                if Clients.show_lengths.get(request.session.session_key) == len(
                        Clients.show_data.get(request.session.session_key)): # All data received
                    has_show = True
                    context['show'] = ""
                    for entry in Clients.show_data.get(request.session.session_key):
                        # Convert messages and images to HTML
                        if entry[0] == 'text':
                            context['show'] += "\nText: " + entry[1]
                        elif entry[0] == 'image':
                            context[
                                'show'] += "\nImage: " + "<img id=\"profileImage\" src=\"data:image/jpg;base64, " + base64.b64encode(
                                entry[1]) + "\">"

                    break
            time.sleep(0.1)
        context['has_show'] = has_show

    if has_connection and request.POST.get('image'):
        # User clicked image button, send to server
        print "User input: send image"
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # Binary representation of image
            image_payload = ClientCallback.create_image(request.FILES['imagefile'], conn)
            try:
                conn.send_payload(image_payload)
            except:
                context['connection_lost'] = True
            context['needs_ack_image'] = True
        else:
            return render(request, 'app/index.html', context)  # Nothing supplied, ignore
        has_ack_image = False
        # Again allow up to 10 seconds for ack
        for i in range(100):
            if Clients.acks.get(request.session.session_key) == image_payload[1]:
                has_ack_image = True
                break
            time.sleep(0.1)
        context['has_ack_image'] = has_ack_image

    return render(request, 'app/index.html', context)


class UploadFileForm(forms.Form):
    imagefile = forms.ImageField()
