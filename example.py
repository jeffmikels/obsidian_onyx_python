import asyncio
import time

from onyx import ObsidianOnyx


HOST = '192.168.50.13'
PORT = 2323


def show_active(client: ObsidianOnyx):
  ts('UPDATE RECEIVED')
  for item in client.cueLists:
    if item.active or item.transitioning:
      print(item)


def ts(obj):
  print(f'{time.time():.3f}: {obj}')


async def main():
  # setup a client... print out all messages, run custom function on
  # backend updates
  print('CONNECTING')
  client = ObsidianOnyx(HOST, PORT, on_update=show_active, on_message=ts)

  # When connected, the client will periodically ask Onyx about the
  # current active cuelists and call the on_update function whenever
  # a cuelist changes status
  await client.connect()
  print('CONNECTED')

  # example of how to select a cuelist by name
  selected = None
  for cl in client.cueLists:
    if cl.name == 'House Half':
      selected = cl
      break
  print(selected)

  # cueLists may also be selected directly using the `cueListMap` dict
  # NOTE: the key is an integer even though it's a dict, not a list
  selected = client.cueListMap[18] or None
  print(selected)

  await asyncio.sleep(6)
  await client.triggerCueList(selected)
  await asyncio.sleep(6)
  await client.releaseCueList(selected)

  # The client will remain active until the script closes
  # but make sure not to block the thread.
  # For example, use asyncio.sleep and not time.sleep
  while client.connected:
    await asyncio.sleep(10)

asyncio.run(main())
