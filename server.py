import aiocoap.resource as resource
import aiocoap
import tinytuya

class AlarmResource(resource.Resource):
    """This resource supports the PUT method.
    PUT: Update state of alarm."""

    def __init__(self):
        super().__init__()
        self.state = "OFF"
        self.bulb1.set_version(3.3)
        self.bulb2.set_version(3.3)
        self.bulb3.set_version(3.3)
        print("Server started")

    async def render_put(self, request):
        self.state = request.payload
        print('sensor: %s' % self.state)

        return aiocoap.Message(code=aiocoap.CHANGED, payload=self.state)