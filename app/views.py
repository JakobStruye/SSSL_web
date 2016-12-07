from django.http import HttpResponse
from django.shortcuts import render
from SSSL.client import Client
from Clients import Clients
from ServerApp import ServerApp
from ServerCallback import ServerCallback
import time
from django import forms
import base64

def index(request):
    ServerApp.get_server()
    if not request.session.get('has_session'): #Force setting session key
        request.session['has_session'] = True
    has_connection = (Clients.clients.get(request.session.session_key) is not None)
    print "SESSKEY", request.session.session_key
    context = {'has_connection': has_connection}
    if not has_connection and request.POST.get('connect'):
        #mypythoncode.mypythonfunction( int(request.POST.get('mytextbox')) )
        client = Client('client-05.pem', 'project-client', 'Konklave123')
        client.add_payload_listener(ServerCallback)
        error = client.connect('localhost', 8970)

        if error == 0:
            Clients.clients[request.session.session_key] = client
            context['has_connection'] = True
        else:
            context['has_connection'] = False
            context['has_error'] = True
            print "err",  error
    
    if request.session.session_key:
        conn = Clients.clients.get(request.session.session_key)
        Clients.client_to_session_key[conn] = request.session.session_key

    if has_connection and request.POST.get('disconnect'):
        print "disconnecting"
        #mypythoncode.mypythonfunction( int(request.POST.get('mytextbox')) )
        
        conn.disconnect()
        Clients.clients[request.session.session_key] = None
        context['has_connection'] = False

    if has_connection and request.POST.get('message'):
        print "message"
        #mypythoncode.mypythonfunction( int(request.POST.get('mytextbox')) )
        message = ServerCallback.create_message(request.POST.get('messagetext'), conn)
        conn.send_payload(message)
        context['needs_ack'] = True
        has_ack = False
        for i in range(100):
            if Clients.acks.get(request.session.session_key) == message[1]:
                has_ack = True
                break
            time.sleep(0.1)
            print "sleep", message[1], Clients.acks.get(request.session.session_key), request.session.session_key, len(Clients.acks), type(request.session.session_key)
        context['has_ack'] = has_ack

    if has_connection and request.POST.get('show'):
        # mypythoncode.mypythonfunction( int(request.POST.get('mytextbox')) )
        Clients.show_ids[request.session.session_key] = None
        message = ServerCallback.create_show(conn)
        conn.send_payload(message)
        context['needs_show'] = True
        has_show = False
        for i in range(100):
            if Clients.show_ids.get(request.session.session_key) is not None: #First reply received
                if Clients.show_lengths.get(request.session.session_key) == len(Clients.show_data.get(request.session.session_key)):
                    has_show = True
                    context['show'] = ""
                    for entry in Clients.show_data.get(request.session.session_key):
                        if entry[0] == 'text':
                            context['show'] += "\nText: " + entry[1]
                        elif entry[0] == 'image':
                            context['show'] += "\nImage: " + "<img id=\"profileImage\" src=\"data:image/jpg;base64, " + base64.b64encode(entry[1])+ "\">"

                    f = open('jipla', 'w')
                    f.write(context['show'])
                    break
            time.sleep(0.1)
        context['has_show'] = has_show

    if has_connection and request.POST.get('image'):
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            image_payload = ServerCallback.create_image(request.FILES['imagefile'], conn)
            conn.send_payload(image_payload)
        context['needs_ack_image'] = True
        has_ack_image = False
        for i in range(100):
            if Clients.acks.get(request.session.session_key) == image_payload[1]:
                has_ack_image = True
                break
            time.sleep(0.1)
        context['has_ack_image'] = has_ack_image

    return render(request,'app/index.html', context)


class UploadFileForm(forms.Form):
    imagefile = forms.ImageField()
