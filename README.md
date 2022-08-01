<div align="center">

# Calamity

_传说中有柄魔剑斩下了灾祸，灾祸带给人们以痛苦以幸福以哀嚎以歌颂，何来彼此._

> 子非鱼，安知鱼之乐

 [![CodeFactor](https://www.codefactor.io/repository/github/luxuncang/calamity/badge)](https://www.codefactor.io/repository/github/luxuncang/lacia)
 [![GitHub](https://img.shields.io/github/license/luxuncang/calamity)](https://github.com/luxuncang/lacia/blob/master/LICENSE)
 [![CodeQL](https://github.com/luxuncang/calamity/workflows/CodeQL/badge.svg)](https://github.com/luxuncang/lacia/blob/master/.github/workflows/codeql-analysis.yml)

</div>

## 安装

```bash
pip install calamity
```

```bash
pdm add calamity
```

## 特性

* 兼容 [Graia Broadcast](https://github.com/GraiaProject/BroadcastControl)
* 兼容 [Lacia](https://github.com/luxuncang/lacia)

## 使用

### 入门

**Server 端**

```python
from calamity import Calamity

Calamity.server()
```

**Client 端**

* 客户端 A

```python
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
```

* 客户端 B

```python
import asyncio

from calamity import Calamity
from graia.broadcast import Broadcast, Dispatchable, BaseDispatcher, DispatcherInterface

loop = asyncio.get_event_loop()
bcc = Broadcast(loop=loop)
bcc = Calamity.patch(debug=True)

class ExampleEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if interface.annotation is str:
                return "Calamity"


@bcc.receiver(ExampleEvent)
async def event_receiver(event: str):
    print("Hello Broadcast!", event)

@bcc.receiver(ExampleEvent)
async def event_receiver1(event: str):
    print("Hello Lacia!", event)

async def main():
    bcc.postEvent(ExampleEvent(), remote=True)

loop.run_until_complete(main())
loop.run_forever()
```

### 提示
```
bcc = Broadcast(loop=loop) # 声明 bcc
bcc = Calamity.patch(debug=True) # remote bcc
```