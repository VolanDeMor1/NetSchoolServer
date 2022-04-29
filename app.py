# Cервер, который будет обрабатывать запросы на получение информации из сайта СГО
#  главное условие: Обрабатывать не через API, а через открытую библиотеку.

import asyncio
import flask
from flask import request
from flask import jsonify
from flask_cors import CORS
from urllib.parse import unquote
import time
from lib import NetSchoolAPI
import json


cache = dict()
app = flask.Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})


def error(msg):
    return jsonify(error=msg, success=None)


def success(msg):
    return jsonify(success=msg, error=None)


def check_session(net_id):
    global cache
    if cache.get(net_id) is not None:
        obj = cache.get(net_id)
        if obj[1] <= round(time.time() * 1000):
            obj[0].logout()
            del cache[net_id]
            return False
        else:
            return True
    else:
        return False


@app.route('/api/login/', methods=['GET'])
async def login():
    global cache

    if 'src' in request.args:
        src = unquote(str(request.args['src']))
    else:
        return error("No src field provided. Please specify an src")
    if 'lg' in request.args:
        lg = unquote(str(request.args['lg']))
    else:
        return error("No id field provided. Please specify an id")

    if 'pw' in request.args:
        pw = unquote(str(request.args['pw']))
    else:
        return error("No password field provided. Please specify a password")

    if 'sch' in request.args:
        sch = unquote(str(request.args['sch']))
    else:
        return error("No school field provided. Please specify an school")

    ns = NetSchoolAPI(src)
    res = await ns.login(lg, pw, sch)

    cookies = ""
    for head in res.headers.multi_items():
        if head[0] == 'set-cookie':
            cookies = head[1]
            break

    net_id = ""
    for cookie in cookies.split("; "):
        data = cookie.split("=")
        if data[0] == "NSSESSIONID":
            net_id = data[1]
            break

    cache[net_id] = [ns, ((time.time() * 1000) + (1000 * 60 * 5))]
    return json.dumps(res.headers.multi_items())


@app.route('/api/logout/', methods=['GET'])
async def logout():
    global cache
    if 'id' in request.args:
        net_id = unquote(str(request.args['id']))
    else:
        return error("No net_id field provided. Please specify a net_id")

    if not (cache.get(net_id) is None):
        cache.get(net_id)[0].logout()
        return success("Logged out")
    else:
        return error("Something went wrong")


@app.route('/api/diary/', methods=['GET'])
async def home():
    global cache
    print(cache)
    if 'id' in request.args:
        net_id = unquote(str(request.args['id']))
    else:
        return error("No net_id field provided. Please specify a net_id")

    if not check_session(net_id):
        return error("Your session is out of date")
    elif cache.get(net_id) is None:
        return error("Something went wrong")
    else:
        return await cache.get(net_id)[0].diary_json()


async def main():
    app.run()


if __name__ == '__main__':
    from waitress import serve

    serve(asyncio.run(main()), host="0.0.0.0", port=8000)
