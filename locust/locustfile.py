"""Trabalho 3: HTML e imagem original, sem cache de navegador."""
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from locust import HttpUser, between, task

MANIFEST = json.loads(Path(__file__).with_name('posts.json').read_text())
SCENARIO = os.getenv('SCENARIO', 'imagem-1mb')
POST = MANIFEST[SCENARIO]


class WordPressUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.headers.update({'Host': 'localhost:8080'})

    @task
    def acessar_post(self):
        with self.client.get('/?p=' + str(POST['id']), name=SCENARIO + '/html',
                             allow_redirects=False, timeout=15, catch_response=True) as r:
            if r.status_code != 200 or POST['marker'] not in r.text:
                r.failure('HTML sem status 200 ou marcador esperado')
                return
            if POST.get('image_url') and POST['image_url'] not in r.text:
                r.failure('Imagem original ausente no HTML')
                return
        if POST.get('image_url'):
            path = urlsplit(POST['image_url']).path
            with self.client.get(path, name=SCENARIO + '/imagem', allow_redirects=False,
                                 timeout=15, catch_response=True) as r:
                if (r.status_code != 200 or len(r.content) != POST['bytes'] or
                        hashlib.sha256(r.content).hexdigest() != POST['sha256']):
                    r.failure('Imagem incompleta, alterada ou status diferente de 200')
