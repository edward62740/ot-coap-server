import aiocoap.resource as resource
import aiocoap
import tinytuya

class RadarResource(resource.Resource):
    """This resource supports the PUT method.
    PUT: Update state of alarm."""


    def __init__(self, uri):
        super().__init__()
        self.path = uri
        self.state = "OFF"
        self.bulb1.set_version(3.3)
        self.bulb2.set_version(3.3)
        self.bulb3.set_version(3.3)
        print("Server started")

    async def render_put(self, request):
        client_ip = request.remote.hostinfo
        print(self.path)
        self.state = request.payload.decode("utf-8")
        print("Received PUT request from " + client_ip + " with payload " + self.state + " and resource " )

        return aiocoap.Message(code=aiocoap.ACK)