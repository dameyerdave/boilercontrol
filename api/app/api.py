import cherrypy
import yaml


class BoilerControl(object):
    exposed = True

    @cherrypy.tools.json_out()
    def GET(self):
        with open('/manual.conf', 'r') as cf:
            manual = yaml.safe_load(cf)

        return manual

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):
        manual = cherrypy.request.json

        with open('/manual.conf', 'w') as cf:
            yaml.dump(manual, cf)

        return manual


if __name__ == '__main__':
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 5000,
    })
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'text/plain')],
        }
    }
    cherrypy.quickstart(BoilerControl(), '/api/', conf)
