import json
from datetime import datetime

from django.conf import settings
from django.db.models import Max
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect

from botshot.core.responses import TextMessage
from botshot.models import MessageLog
from botshot.webchat.interface import WebchatInterface
from .forms import MessageForm

if 'botshot.core.logging.db.DbLogger' not in settings.BOT_CONFIG.get("MESSAGE_LOGGERS", []):
    raise AssertionError("Webchat requires DbLogger. Please add botshot.logging.db.DbLogger to MESSAGE_LOGGERS in your BOT_CONFIG.")


def webchat(request):
    # if 'uid' not in request.session:  TODO login
    #     return render(request, 'botshot/webchat/welcome.html')

    # uid = request.session['uid']
    uid = "web___0"

    if request.method == 'POST':
        # message received via webchat
        if request.POST.get('message'):
            message_text = request.POST.get('message')
            #data = json.dumps(TextMessage(message_text).to_response())

            # process message if text != null
            if request.POST.get("postback"):
                postback = request.POST.get("postback")
                WebchatInterface.accept_postback(uid, message_text, postback)
            else:
                WebchatInterface.accept_request(uid, message_text)
        else:
            print("Error, message not set in POST")
            return HttpResponseBadRequest()
        return HttpResponse()

    else:
        # send chat page
        messages = MessageLog.objects.filter(chat__chat_id="web_"+uid).order_by('time')
        for m in messages:
            try:
                m.meta_raw = json.loads(m.meta_raw)
            except:
                pass

        # messages = [_convert_to_old_format(message) for message in messages]
        context = {
            'uid': uid, 'messages': messages,
            'form': MessageForm, 'timestamp': datetime.now().timestamp(),
            'user_img': settings.BOT_CONFIG.get('WEBCHAT_USER_IMAGE', 'images/icon_user.png'),
            'bot_img': settings.BOT_CONFIG.get('WEBCHAT_BOT_IMAGE', 'images/icon_robot.png')
        }
        return render(request, 'botshot/webchat/index.html', context)


def do_login(request):
    if request.method == 'POST' and 'username' in request.POST:
        username = request.POST.get('username')
        uid = WebchatInterface.make_uid(username)
        request.session['uid'] = uid
        request.session['username'] = username
        return HttpResponse()
    else:
        return HttpResponseBadRequest()


def do_logout(request):
    if 'uid' in request.session:
        WebchatInterface.destroy_uid(request.session['uid'])
        del request.session['uid']
        del request.session['username']
    return redirect('webchat')


def get_last_change(request):
    uid = "web___0"
    if 'uid' in request.session or True:
        # uid = request.session['uid']
        max_time = MessageLog.objects.filter(chat__chat_id="web_"+uid).aggregate(Max('time'))
        timestamp = max_time.get('time__max')
        timestamp = timestamp.timestamp() if timestamp else 0
        return JsonResponse({'timestamp__max': timestamp})
    return HttpResponseBadRequest()


def _convert_to_old_format(message: MessageLog):
    # TODO replace with new format
    obj = {"timestamp": message.time.timestamp()}
    if message.is_from_user:
        obj['is_response'] = False
        obj['message'] = {"text": message.text},
    else:
        obj['is_response'] = True
        obj['message'] = message.meta_raw
    return obj
