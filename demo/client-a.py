import asyncio

from calamity import Calamity
from graia.broadcast import Broadcast, Dispatchable, BaseDispatcher, DispatcherInterface

loop = asyncio.get_event_loop()
bcc = Broadcast(loop=loop)
bcc = Calamity.patch()

class ExampleEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if interface.annotation is str:
                return "Calamity"


@bcc.receiver(ExampleEvent, remote=True)
async def event_receiver(event: str):
    print("Hello Broadcast!", event)

@bcc.receiver(ExampleEvent)
async def event_receiver1(event: str):
    print("Hello Lacia!", event)

async def main():
    bcc.postEvent(ExampleEvent())

loop.run_until_complete(main())
loop.run_forever()