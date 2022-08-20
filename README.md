# Obsidian Onyx Lighting Control Library for Python

This is a very simple Python library for interacting with the Telnet API of Onyx Lighting control by [Obsidian Control Systems](https://obsidiancontrol.com/).

# Instructions

## Install:

```bash
python3 setup.py install
```

Or simply place a copy of the `onyx` folder in your working directory or your Python path.

## Setup Onyx Manager

This library WILL NOT WORK unless the "Onyx Manager" program is running on your Onyx controller. Once it is running, make sure to enable the Telnet Server and check the port number it runs on. (Usually 2323).

Additionally, this library needs to run on a device that has network connectivity to your Onyx controller.

Finally, you need to know the IP address of your Onyx controller before you can use this library.

## Usage

See the example.py script in this folder or consider this even more simplified example.

```python
import asyncio
from onyx import ObsidianOnyx

HOST = '192.168.50.13'
PORT = 2323

async def main():
  # setup a client... print out all messages, run custom function on
  # backend updates
  print('CONNECTING')
  client = ObsidianOnyx(HOST, PORT, on_update=show_active, on_message=print)

  # When connected, the client will periodically ask Onyx about the
  # current active cuelists and call the on_update function whenever
  # a cuelist changes status
  await client.connect()
  print('CONNECTED')

  # Select the cueList marked `00001`
  selected = client.cueListMap[1] or None
  print(selected)
  await client.triggerCueList(selected)

  # wait until the cueList is active
  while not selected.active:
    await asyncio.sleep(1)

  print('CUELIST IS NOW ACTIVE... RELEASING AFTER 3 SECONDS')
  await asyncio.sleep(3)
  await client.releaseCueList(selected)

  # wait until the cueList is no longer active
  # (this time we are watching the "transitioning" flag instead of the active status)
  while selected.transitioning:
    await asyncio.sleep(1)

  print('CUELIST IS BACK TO NORMAL... QUITTING')


asyncio.run(main())
```

# Reference

Once connected, the library will load all the available cue lists from Onyx, and it will initiate a persistent loop requesting updates from Onyx every second. However, if the library is used to trigger or release a cue list, the update frequency will increase to give more accuracy during the time a cue list is transitioning.

## Classes

### ObsidianOnyx

#### Properties

-   cueLists: list[OnyxCueList] -> a list of all available OnyxCueList items
-   cueListMap: dict[int, OnyxCueList] -> dictionary indexed to OnyxCueList number (as integer)
-   transport: asyncio.Transport -> low-level direct access to the TCP socket
-   connected: bool = None -> True when connected
-   first_message: OnyxMessage = None -> stores the Onyx welcome message on connection
-   on_update: Callable[[], None] = None -> callback called whenever a CueList updates
-   on_message: Callable[[OnyxMessage], None] = None -> callback called whenever a message is received from Onyx

#### Methods

-   loadAll() -> manually reload all CueLists and CueList statuses
-   loadAvailable() -> manually reload all CueLists, but not their statuses
-   loadActive() -> manually request a CueList status update from Onyx
-   sendCmd(cmd: str, boost: bool = False) -> will send any command to Onyx. This function is `async` and must be called with `await`. It returns an `OnyxMessage`.

All other methods are documented in the `onyx.py` file

### OnyxMessage

`sendCmd()` and most of the other methods in the `ObsidianOnyx` class return an `OnyxMessage` object when awaited.

#### Properties

-   type: str # will be 'info' or 'data' / data responses have multiple lines of data
-   code: int # http response code like 200 on successful requests
-   message: str # String representation of the returned data
-   data: list[str] # list of each data line in the response

### OnyxCueList

#### Properties

-   parent: OnyxObsidian -> reference to the parent object of this cue list
-   num: str -> the cue list number kept as a string, i.e. "00018"
-   name: str -> the cue list name as stored in Onyx
-   value: int -> some cue lists have a value associated with them
-   active: bool -> is the cue list currently active
-   transitioning: bool -> computed property, true whenever a cuelist is transitioning

#### Methods

Although cue lists can be triggered and controlled directly from the ObsidianOnyx class methods, sometimes it's easier to call them from the cue list object itself. As a result, each cue list retains a reference to its 'parent' which allows the following methods to exist on the cue list objects.

-   trigger() -> triggers the cuelist
-   triggerCue(nuber) -> triggers an individual cue in the cuelist according to `number`
-   pause() -> pause the cuelist (if pausing makes sense for that cue list)
-   release() -> releases the cuelist entirely
-   setLevel(value) -> sets the level of a cuelist to `value` (between 0 and 255)
-   reloadActive() -> manually update the active status of this cuelist with a new request to Onyx.
-   reloadName() -> manually update the name of this cuelist with a new request to Onyx.
