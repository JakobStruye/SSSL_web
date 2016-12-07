from django.http import HttpResponse
from django.shortcuts import render
from SSSL.client import Client
from Clients import Clients
from ServerApp import ServerApp
from ServerCallback import ServerCallback
import time

def index(request):
    ServerApp.get_server()
    has_connection = (Clients.clients.get(request.session.session_key) is not None)

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
        print "show"
        # mypythoncode.mypythonfunction( int(request.POST.get('mytextbox')) )
        message = ServerCallback.create_show(conn)
        conn.send_payload(message)
        context['needs_ack'] = True
        has_ack = False
        for i in range(100):
            if Clients.acks.get(request.session.session_key) == message[1]:
                has_ack = True
                break
            time.sleep(0.1)
            print "sleep", message[1], Clients.acks.get(
                request.session.session_key), request.session.session_key, len(Clients.acks), type(
                request.session.session_key)
        context['has_ack'] = has_ack

    return render(request,'app/index.html', context)
