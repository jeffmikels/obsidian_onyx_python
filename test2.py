import time
import asyncio

completer: asyncio.Future = None


def ts(s: str):
  print(f'{time.time()}: {s}')


async def defer():
  ts('called defer')
  await asyncio.sleep(4)
  ts('sleep is finished')
  completer.set_result('finished')


async def start():
  global completer
  ts('called start')
  loop = asyncio.get_event_loop()
  completer = loop.create_future()
  res = asyncio.wait_for(completer, 5)
  try:
    return await res
  except:
    print('timeout')


async def main():
  loop = asyncio.get_event_loop()
  # loop.run_until_complete(defer)
  both = [defer(), start()]
  res = await asyncio.wait(both)
  ts(res)


asyncio.run(main())
