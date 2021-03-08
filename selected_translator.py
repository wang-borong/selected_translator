#!/usr/bin/env python3

import os
import io
import sys
import requests
import argparse
import threading
from enum import Enum
from urllib import request, parse
from pydub import AudioSegment
# request pydub and simpleaudio library
from pydub.playback import play


class TransType(Enum):
    google = {'api': 'https://translate.googleapis.com/',
              'function': {'translate': 'translate_a/single?client=gtx'\
                           '&sl={sl}&tl={tl}&dt=at&dt=bd&dt=ex&dt=ld&dt=md'\
                           '&dt=qca&dt=rw&dt=rm&dt=ss&dt=t&q={text}',
                           'speak': 'translate_tts?ie=utf-8&client=gtx&'\
                           'tl={stl}&q={text}',
                           }
             }

class Translator:
    def __init__(self, sl, tl, text, trans_type=TransType.google.value):
        self.trans_type = trans_type
        self.sl = sl
        self.tl = tl
        self.orgtext = text
        self.text = parse.quote_plus(text)

        session = requests.Session()
        session.headers = {'User-Agent': 'Firefox'}
        trans_url = self._retrieve_trans_url()
        self.json = session.get(trans_url, timeout=2).json()
        self.sl = self.json[2]
        self.target_text = parse.quote_plus(self.json[0][0][0])

    def _retrieve_trans_url(self):
        trans_url = self.trans_type['api'] + \
            self.trans_type['function']['translate'].format(
                sl=self.sl, tl=self.tl, text=self.text)
        return trans_url

    def _retrieve_speak_url(self, lang, text):
        speak_url = self.trans_type['api'] + \
            self.trans_type['function']['speak'].format(
                stl=lang, text=text)
        return speak_url

    def translate(self):
        results = self.orgtext
        res_json = self.json

        if len(res_json[0][1]) > 3 and res_json[0][1][3] != None:
            results = results + '  /' + res_json[0][1][3] + '/\n'
        else:
            results += '\n'

        results = results + res_json[0][0][0]
        if res_json[1]:
            results = results + '\n--- --- --- --- --- ---'\
                                ' --- --- --- --- --- ---\n'
            for data in res_json[1]:
                results = results + '{}\n'.format(data[0])
                for d in data[2]:
                    results = results + '    {}: {}\n'.format(d[0], ", ".join(d[1]))

        return results

    def _speak(self, lang, text):
        speak_url = self._retrieve_speak_url(lang, text)
        speak_req = request.Request(speak_url,
                                    headers = { "User-Agent": "Firefox" })
        data = request.urlopen(speak_req ,timeout=2).read()
        sound = AudioSegment.from_file(io.BytesIO(data), format="mp3")
        play(sound)

    def speak(self):
        self._speak(self.sl, self.text)
        self._speak(self.tl, self.target_text)

def save_history(histfile, text):
    if not os.path.exists(os.path.dirname(histfile)):
        os.makedirs(os.path.dirname(histfile))
    if os.path.exists(histfile):
        sep = '=====================================================\n\n'
        text = sep + text
    text = text + '\n'
    with open(histfile, 'a+') as hf:
        hf.write(text)

def xclip_grap_words():
    selected_text = os.popen('xclip -out -selection').read() #X11 Only

    if selected_text == "":
        log_print("No selected text in memory ...")
        sys.exit(0);

    return selected_text

def wrap_display(func):
    def inner(text):
        func(text)
        try:
            histfile = os.path.expanduser('~/.cache/google_translate/history')
            save_history(histfile, text)
        except:
            log_print('Save history file failed ...')
    return inner

@wrap_display
def tk_display(text):
    import tkinter as tk
    def quit(event):
        top.quit()
    top = tk.Tk()
    tex = tk.Text(master=top)
    tex.pack(side=tk.RIGHT)
    tex.insert(tk.END, text)
    # Scroll if necessary
    tex.see(tk.END)
    top.bind('<Control-w>', quit)
    top.bind('<Control-q>', quit)
    top.mainloop()

@wrap_display
def gtk_display(text):
    # request gobject
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    window = Gtk.Window()
    window.connect("delete-event", Gtk.main_quit)
    window.connect("leave-notify-event", Gtk.main_quit)
    window.set_position(Gtk.WindowPosition.MOUSE)
    label = Gtk.Label(text)
    label.set_use_markup(True)
    label.set_selectable(True)
    #label.set_line_wrap(True)
    label.set_can_focus(True)
    label.set_max_width_chars(50)
    label.set_margin_top(10)
    label.set_margin_bottom(10)
    window.add(label)
    window.set_decorated(False)
    window.set_keep_above(True)
    window.show_all()
    Gtk.main()

@wrap_display
def terminal_display(text):
    print(text)

def notify(msg):
    try:
        import pynotify
        pynotify.init("GT")
        notice = pynotify.Notification('google_translate', msg)
        notice.show()
    except:
        import subprocess
        subprocess.Popen(['notify-send', '--app-name=google_translate', msg])

def main():
    dest_lang = 'zh-CN'
    if len(sys.argv) == 1:
        words = xclip_grap_words()
    else:
        words = ''
        for i in range(1, len(sys.argv)):
            words += sys.argv[i]
            words += ' '

    if len(words) > 5000:
        log_print('Maximum characters exceeded ...')
        return 1

    translator = Translator('auto', 'zh-CN', words)
    threading.Thread(target=translator.speak).start()
    display(translator.translate())

if sys.stdout.isatty() or len(sys.argv) > 1:
    log_print = print
    display = terminal_display
else:
    log_print = notify
    display = gtk_display

main()
