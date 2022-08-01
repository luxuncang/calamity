from __future__ import annotations

import sys
import asyncio
import inspect
import pickle
from functools import partial
from abc import ABC, abstractclassmethod
from typing import (
    Optional,
    TypeVar,
    Generic,
    Callable,
    List,
    Type,
    Union,
    cast,
    Iterable,
)

if sys.version_info >= (3, 10):
    from typing import ParamSpec, Concatenate
else:
    from typing_extensions import ParamSpec

from lacia import JsonRpc, logger, AioClient, AioServer
from graia.broadcast import (
    Broadcast,
    Namespace,
    Decorator,
    T_Dispatcher,
    dispatcher_mixin_handler,
    CoverDispatcher,
    group_dict,
    PropagationCancelled
)
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities import listener
from graia import broadcast

T = TypeVar("T")
P = ParamSpec("P")


class AbcCalamity(ABC):
    @abstractclassmethod
    def receiver(self):
        ...

    @abstractclassmethod
    def post_event(self):
        ...

    @abstractclassmethod
    def patch(self):
        ...

    @abstractclassmethod
    def client(self):
        ...

    @abstractclassmethod
    def server(self):
        ...


class Calamity(AbcCalamity, Generic[T, P]):
    rpc: JsonRpc
    bcc: Broadcast
    loop: asyncio.AbstractEventLoop
    task: asyncio.Task
    Events: List[Union[str, Type[Dispatchable]]]

    @classmethod
    def server(
        cls,
        host: str = "localhost",
        port: int = 8080,
        path: str = "/chris",
        debug: bool = False,
    ):
        cls.loop = asyncio.get_event_loop()
        cls.rpc = JsonRpc(
            host=host,
            port=port,
            path=path,
            namespace={"post_event": cls.reverse_post_event},
            loop=cls.loop,
            debug=debug
        )
        cls.rpc.run_server(AioServer())

    @classmethod
    async def client(cls):
        await cls.rpc.run_client(AioClient())

    @classmethod
    def patch(
        cls,
        host: str = "localhost",
        port: int = 8080,
        path: str = "/chris",
        debug: bool = False,
    ):
        frame = inspect.currentframe()
        try:
            cls.loop = cls.get_type_obj(asyncio.AbstractEventLoop, frame)
            cls.bcc = cls.get_type_obj(Broadcast, frame)
        except ValueError:
            logger.error("Please declare EventLoop and broadcast before patch")
            raise ValueError

        cls.rpc = JsonRpc(
            host=host,
            port=port,
            path=path,
            namespace={"post_event": cls.post_event},
            loop=cls.loop,
            debug=debug
        )
        cls.bcc.receiver
        task = cls.loop.create_task(cls.client())
        cls.task = task
        return cls.__hook_bcc()

    @classmethod
    def receiver(cls):
        print("Chris is the receiver")

    @classmethod
    def post_event(
        cls, 
        event,
        upper_event,
        remote: bool = False,
    ):
        cls.bcc.postEvent(event, upper_event)
        return True

    @classmethod
    def reverse_post_event(
        cls,
        event,
        upper_event,
        remote: bool = False,
        ):
        frame = inspect.currentframe()
        ws = cls.rpc.get_ws(frame)
        wss = list(filter(lambda x: not ws is x[0] ,cls.rpc._server.active_connections))
        for i in wss:
            cls.loop.create_task(cls.rpc.send_request_server(cls.rpc.post_event(event, upper_event), i[0]))
        return True
        
   
    @classmethod
    def get_type_obj(cls, typer, frame):
        for local in cls.__frame_locals(frame):
            for _, v in local.items():
                if isinstance(v, typer):
                    return v
        raise ValueError("Not found type obj")

    @staticmethod
    def __frame_locals(frame):
        frame = frame.f_back  # type: ignore
        while frame:
            yield frame.f_locals
            frame = frame.f_back

    @classmethod
    def __hook_bcc(cls):
        class Listener(listener.Listener):
            def __init__(
                self,
                callable: Callable,
                namespace: Namespace,
                listening_events: List[Type[Dispatchable]],
                inline_dispatchers: Optional[List[T_Dispatcher]] = None,
                decorators: Optional[List[Decorator]] = None,
                priority: int = 16,
                remote: bool = False,
            ) -> None:
                self.remote = remote
                return super().__init__(
                    callable,
                    namespace,
                    listening_events,
                    inline_dispatchers,
                    decorators,
                    priority,
                )

        listener.Listener = Listener

        class Broadcast(broadcast.Broadcast):
            def receiver(
                self,
                event: Union[str, Type[Dispatchable]],
                priority: int = 16,
                dispatchers: Optional[List[T_Dispatcher]] = None,
                namespace: Optional[Namespace] = None,
                decorators: Optional[List[Decorator]] = None,
                remote: bool = False,
            ):
                if isinstance(event, str):
                    _name = event
                    event = self.findEvent(event)  # type: ignore
                    if not event:
                        raise InvalidEventName(_name + " is not valid!")  # type: ignore
                priority = int(priority)

                def receiver_wrapper(callable_target):
                    listener = self.getListener(callable_target)
                    if not listener:
                        self.listeners.append(
                            Listener(
                                callable=callable_target,
                                namespace=namespace or self.getDefaultNamespace(),
                                inline_dispatchers=dispatchers or [],
                                priority=priority,
                                listening_events=[event],  # type: ignore
                                decorators=decorators or [],
                                remote=remote,
                            )
                        )
                    elif event in listener.listening_events:
                        raise RegisteredEventListener(event.__name__, "has been registered!")  # type: ignore
                    else:
                        listener.listening_events.append(event)  # type: ignore
                    return callable_target

                return receiver_wrapper

            def postEvent(
                self,
                event: Dispatchable,
                upper_event: Optional[Dispatchable] = None,
                remote: bool = False,
            ):
                listener_generator: Iterable[Listener] = self.default_listener_generator(event.__class__)  # type: ignore  
                if isinstance(event, bytes) and isinstance(upper_event, bytes):  
                    event = pickle.loads(event)
                    upper_event = pickle.loads(upper_event)
                    listener_generator: Iterable[Listener] = self.default_listener_generator(event.__class__)  # type: ignore
                    listener_generator = list(filter(lambda x: x.remote, listener_generator))
                else:
                    if remote:
                        levent = pickle.dumps(event)  # type: ignore
                        lupper_event = pickle.dumps(upper_event)  # type: ignore

                        async def _post_event():
                            while not cls.task.done():
                                await asyncio.sleep(0.5)
                            await cls.rpc.post_event(levent, lupper_event)
                        cls.loop.create_task(_post_event())  # type: ignore
                task = self.loop.create_task(
                    self.layered_scheduler(
                        listener_generator=listener_generator,  # type: ignore
                        event=event,
                        addition_dispatchers=[
                            CoverDispatcher(i, upper_event)
                            for i in dispatcher_mixin_handler(upper_event.Dispatcher)
                        ]
                        if upper_event
                        else [],
                    )
                )
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
                return task

        cls.bcc.receiver = partial(Broadcast.receiver, cls.bcc)  # type: ignore
        cls.bcc.postEvent = partial(Broadcast.postEvent, cls.bcc)  # type: ignore
        return cast(Broadcast, cls.bcc)
