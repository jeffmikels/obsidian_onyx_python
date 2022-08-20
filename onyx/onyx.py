import asyncio
import re
from time import time

from typing import Callable
from __future__ import annotations

from dataclasses import dataclass

from .exceptions import ObsidianOnyxError


msg_info_search = re.compile(r'^(\d\d\d)([- ])(.*)')
cuelist_info_search = re.compile(r'^(\d+) - (.*)')


@dataclass
class OnyxMessage:
  """onyx runs on a Windows machine, so it uses Windows line endings
  \r\n

  All responses have a minimum of three lines.
  There are two kinds of responses;

  "info" responses look like this

  ```text
  HTTPCODE-TEXTLINE 1
  HTTPCODE-TEXTLINE 2
  HTTPCODE command sent by user if there was one
  ```

  for example, when a client first connects, we get three lines:

  ```text
  200-*************Welcome to Onyx Manager v4.0.1010 build 0!*************
  200-Type HELP for a list of available commands
  200
  ```

  after an invalid command like 'hello', we get:

  ```text
  400-I never heard that command before... are you sure?
  400-Type HELP for a list of commands
  400 hello
  ```

  "data" responses are terminated by a dot on a line by itself

  ```text
  HTTPCODE Ok
  response data over many lines
  .
  ```

  after qlactive, we get this:

  ```text
  200 Ok
  No Active Qlist in List
  .
  ```

  after qllist, we get this:

  ```text
  200 Ok
  00002 - House Lights
  00003 - SlimPar
  00004 - LED Tape
  ... other items ...
  .
  ```"""
  type: str  # should be 'info' or 'data'
  code: int
  message: str
  data: list[str]


@dataclass
class OnyxCueList:
  """CueLists will show up like this:

  ```text
  200 Ok
  00002 - House Lights
  00003 - SlimPar
  00004 - LED Tape
  00005 - Bulbs
  ```"""
  parent: ObsidianOnyx

  num: str
  name: str

  # defaults
  value: int = 0  # for cuelists that can do a value
  active: bool = False
  _transitioning_to: bool = None

  @property
  def transitioning(self) -> bool:
    return self._transitioning_to is not None

  async def trigger(self):
    return await self.parent.triggerCueList(self)

  async def triggerCue(self, num: int):
    return await self.parent.triggerCue(self, num)

  async def pause(self):
    return await self.parent.pauseCueList(self)

  async def release(self):
    return await self.parent.releaseCueList(self)

  async def setLevel(self, level: int):
    '''level must be between 0 and 255'''
    return await self.parent.setCueListLevel(self, level)

  async def reloadActive(self):
    self.active = await self.parent.isCueListActive(self)

  async def reloadName(self):
    self.name = await self.parent.getCueListName(self)


class _OnyxClientProtocol(asyncio.Protocol):
  def __init__(self, connect_message, on_close: Callable, on_message: Callable[[OnyxMessage], None] = None):
    self.message = connect_message
    self.on_close = on_close
    self.on_message = on_message
    self.accumulator = ''

  def connection_made(self, transport):
    transport.write(self.message.encode())
    # print('Data sent: {!r}'.format(self.message))

  def data_received(self, data):
    self.accumulator += data.decode()
    # print('Data Received:')
    # print('Data received: {!r}'.format(self.accumulator))
    # print(self.accumulator)
    for message in self.parse_messages():
      self.on_message is None or self.on_message(message)

  def connection_lost(self, exc):
    # print('The server closed the connection')
    self.on_close()

  def parse_messages(self) -> list[OnyxMessage]:
    '''Remember, a full message will have at least three lines,
    and therefore, four \\r\\n pairs'''

    lines = self.accumulator.split('\r\n')
    if len(lines) < 4:
      return []

    current: OnyxMessage = None
    results: list[OnyxMessage] = []
    buffer: list[str] = []

    while len(lines) > 0:
      line = lines.pop(0)

      if line == '.':
        if current is not None:
          results.append(current)
          current = None
        buffer.clear()
        continue
      if line == '' and current is None:
        continue

      # this is a real line
      buffer.append(line)
      matches = msg_info_search.findall(line)

      # is this a continuation of a previous message
      if current is not None:
        if current.type == 'data':
          current.data.append(line)
        else:
          if line == '':
            results.append(current)
            buffer.clear()
            current = None
          if len(matches) > 0:
            code, flag, content = matches[0]
            current.data.append(content)
            current.message = '\r\n'.join(current.data)
        continue

      # is this a new message
      if len(matches) > 0:
        code, flag, content = matches[0]
        t = 'info' if flag == '-' else 'data'
        data = [content] if t == 'info' else []
        current = OnyxMessage(t, code, content, data)
        continue

      # if here, we have an unknown line
      else:
        print(f'I could not understand this response line: {line}')
        print('I have to invalidate the current message')
        buffer.clear()
        # exit()

    # all the lines have been processed
    self.accumulator = '\r\n'.join(buffer)
    # print(results)
    return results


class ObsidianOnyx:
  cueLists: list[OnyxCueList]
  cueListMap: dict[int, OnyxCueList]
  transport: asyncio.Transport
  completer: asyncio.Future = None
  connected: bool = False
  first_message: OnyxMessage = None
  on_update: Callable[[], None] = None
  on_message: Callable[[OnyxMessage], None] = None

  def __init__(self, host, port, on_update: Callable[[], None] = None, on_message: Callable[[OnyxMessage], None] = None):
    self.host = host
    self.port = port
    self._boost_time = 0
    self.on_message = on_message
    self.on_update = on_update
    self.cueLists = []
    self.cueListMap = {}
    self.connected = False

  def _internal_on_message(self, msg: OnyxMessage):
    # print(f'received message: {msg}')
    if self.on_message is not None:
      self.on_message(msg)

    # don't call completer on first message
    # or we will be out of sync
    if self.first_message is None:
      self.first_message = msg
    if self.completer is not None:
      self.completer.set_result(msg)

  def _on_close(self):
    if self.connected:
      self.transport.close()
      self.connected = False

  async def connect(self):
    self.first_message = None
    loop = asyncio.get_running_loop()
    self.completer = loop.create_future()
    transport, protocol = await loop.create_connection(
        lambda: _OnyxClientProtocol(
            '',
            self._on_close,
            self._internal_on_message
        ), self.host, self.port)
    self.transport = transport
    self.connected = True
    await self.loadAll()
    print('starting timer')
    asyncio.ensure_future(self._loop())

  def _notify(self):
    self.on_update is None or self.on_update(self)

  async def sendCmd(self, cmd: str, boost: bool = False) -> OnyxMessage:
    if self.completer is not None:
      # print('waiting for previous command to complete')
      await self.completer
      self.completer = None

    if boost:
      self._boost_time = 3

    loop = asyncio.get_event_loop()
    self.completer = loop.create_future()

    cmd += '\r\n'
    tosend = cmd.encode()
    # print(f'sending: {tosend}')
    self.transport.write(tosend)
    future = asyncio.wait_for(self.completer, 2)
    try:
      res = await future
      # print(f'SUCCESS: received response for {tosend}')
    except asyncio.exceptions.TimeoutError:
      # print(f'TIMEOUT: while waiting for response to {tosend}')
      res = None
    return res

  #
  # These functions handle the internal state of this class
  #
  async def _loop(self):
    if self.connected:
      next_tick = 0.2 if self._boost_time > 0 else 1
      self._boost_time -= next_tick
      await self.loadActive()
      await asyncio.sleep(next_tick)
      await self._loop()

  async def loadAll(self):
    await self.loadAvailable()
    await self.loadActive()

  async def loadAvailable(self):
    m = await self.getAvailableCueLists()
    self.cueLists.clear()
    self.cueListMap.clear()
    for item in m.data:
      cl = parse_cuelist(self, item)
      if cl is not None:
        self.cueListMap[int(cl.num)] = cl
        self.cueLists.append(cl)
    self._notify()

  async def loadActive(self):
    dirty = False
    m = await self.getActiveCueLists()
    active_nums = []
    for item in m.data:
      cl = parse_cuelist(self, item)
      if cl is not None:
        active_nums.append(cl.num)

    # update existing cuelist, match by number
    for existing in self.cueLists:
      was_active = existing.active
      is_active = existing.num in active_nums
      if is_active != was_active:
        dirty = True
        existing.active = is_active
      if existing._transitioning_to == is_active:
        dirty = True
        existing._transitioning_to = None

    if dirty:
      self._notify()

  '''
  #/ =======================================================
  #/ ONYX API COMMANDS START HERE
  #/ These commands will return Futures for bool, string, or OnyxMessage
  '''

  async def startActionGroup(self, groupNumber):
    '''
    ACT
    [ACT #] -Action Group =  where # is the Action Group Number
    '''
    return await self.sendCmd(f'ACT {groupNumber}')

  async def getActionList(self):
    '''
    ActList
    [ActList] -Will return the Maxxyz Manager Action List
    '''
    return await self.sendCmd(f'ActList')

  async def getActionName(self, actionNumber):
    '''
    ActName
    [ActName #] -Will return the name of Maxxyz Manager Action name
    '''
    result = await self.sendCmd(f'ActName {actionNumber}')
    return result.data[0]

  async def disconnect(self):
    '''
    BYE
    [Bye] -Disconnect from server
    '''
    return await self.sendCmd(f'BYE')

  async def clearProgrammer(self):
    '''
    CLRCLR
    [CLRCLR] -Clear+Clear (clear the programmer)
    '''
    return await self.sendCmd(f'CLRCLR')

  async def triggerCommand(self, commandNumber):
    '''
    CMD
    [CMD #] -Internal Command where # is the Command Number
    '''
    return await self.sendCmd(f'CMD {commandNumber}', True)

  async def getCommandList(self):
    '''
    CmdList
    [CmdList] -Will return the Maxxyz Manager Command List
    '''
    return await self.sendCmd(f'CmdList')

  async def getCommandName(self, commandNumber):
    '''
    CmdName
    [CmdName #] -Will return the name of Maxxyz Manager Command name #
    '''
    result = await self.sendCmd(f'CmdName {commandNumber}')
    return result.data[0]

  async def triggerSchedule(self, scheduleNumber):
    '''
    GSC
    [GSC #] -Go Schedule  where # is the Schedule Number (Set this schdule as default schedule)
    To return to calendar rules use the SchUseCalendar command
    '''
    return await self.sendCmd(f'GSC {scheduleNumber}', True)

  async def triggerCueList(self, cueList):
    '''
    GQL
    [GQL #] -Go Cuelist where # is the Cuelist Number
    '''
    cueList._transitioning_to = True
    self._notify()
    return await self.sendCmd(f'GQL {cueList.num}', True)

  async def triggerCue(self, cueList: OnyxCueList, cueNumber: int):
    '''
    GTQ
    [GTQ #,#] -Go to Cuelist where first # is the Cuelist Number and second # is Cue number
    '''
    result = await self.sendCmd(f'GTQ {cueList.num},{cueNumber}', True)
    return result

  async def getHelp(self):
    '''
    Help
    Displays commands that the servers supports.
    '''
    return await self.sendCmd(f'Help')

  async def isMxRun(self):
    '''
    IsMxRun
    [IsMxRun] -Will return the state of Maxxyz (Yes or No)
    '''
    result = await self.sendCmd(f'IsMxRun')
    return (result.data[0].toLowerCase() == 'yes')

  async def isCueListActive(self, cueList: OnyxCueList):
    '''
    IsQLActive
    [IsQLActive #] -Will return the state of Qlist # (Yes or No)
    '''
    result = await self.sendCmd(f'IsQLActive {cueList.num}')
    return (result.data[0].toLowerCase() == 'yes')

  async def isSchRun(self):
    '''
    IsSchRun
    [IsSchRun] -Will return the Scheduler state (yes or no)
    '''
    result = await self.sendCmd(f'IsSchRun')
    return (result.data[0].toLowerCase() == 'yes')

  async def getRecentLog(self, numLines):
    '''
    Lastlog
    [LastLog #] -Retrun the number of specified log lines starting from the last...
    Example,  LastLog 10 will return the 10 last entry in the log.
    300 Lines max
    '''
    return await self.sendCmd(f'Lastlog {numLines}')

  async def pauseCueList(self, cueList: OnyxCueList):
    '''
    PQL
    [PQL #] -Pause Cuelist where # is the Cuelist Number
    '''
    return await self.sendCmd(f'PQL {cueList.num}')

  async def getActiveCueLists(self):
    '''
    QLActive
    [QLActive] -Will return a list of the current active cuelist
    '''
    return await self.sendCmd(f'QLActive')

  async def getAvailableCueLists(self):
    '''
    QLList
    [QLList] -Will return a list of the avaialble Cuelist
    '''
    return await self.sendCmd(f'QLList')

  async def getCueListName(self, cueListNumber):
    '''
    QLName
    [QLName #] -Will return the name of Maxxyz Cuelist #

    WARNING: DOES NOT WORK with some versions of Onyx
    command will probably timeout
    '''
    result = await self.sendCmd(f'QLName {cueListNumber}')
    return result.data[0] or ''

  async def releaseAllOverrides(self):
    '''
    RAO
    [RAO] -Release All Override
    '''
    return await self.sendCmd(f'RAO', True)

  async def releaseAllCuelists(self):
    '''
    RAQL
    [RAQL] -Release All Cuelist
    '''
    # manually flag all as transitioning
    for cueList in self.cueLists:
      if (cueList.active):
        cueList._transitioning_to = False
    self._notify()
    return await self.sendCmd(f'RAQL', True)

  async def releaseAllCuelistsDimFirst(self):
    '''
    RAQLDF
    [RAQLDF] -Release All Cuelist Dimmer First
    '''
    for cueList in self.cueLists:
      if cueList.active:
        cueList._transitioning_to = False
    self._notify()
    return await self.sendCmd(f'RAQLDF', True)

  async def releaseAllCuelistsAndOverrides(self):
    '''
    RAQLO
    [RAQLO] -Release All Cuelist and Override
    '''
    for cueList in self.cueLists:
      if cueList.active:
        cueList._transitioning_to = False
    self._notify()
    return await self.sendCmd(f'RAQLO', True)

  async def releaseAllCuelistsAndOverridesDimFirst(self):
    '''
    RAQLODF
    [RAQLODF] -Release All Cuelist and Override Dimmer First
    '''
    for cueList in self.cueLists:
      if cueList.active:
        cueList._transitioning_to = False
    self._notify()
    return await self.sendCmd(f'RAQLODF', True)

  async def releaseCueList(self, cueList: OnyxCueList):
    '''
    RQL
    [RQL #] -Release Cuelist where # is the Cuelist Number
    '''
    cueList._transitioning_to = False
    self._notify()
    return await self.sendCmd(f'RQL {cueList.num}', True)

  async def getScheduleList(self):
    '''
    SchList
    [SchList] -Will return the Maxxyz Manager Schedule List
    '''
    return await self.sendCmd(f'SchList')

  async def getScheduleName(self, scheduleNumber):
    '''
    SchName
    [SchName #] -Will return the name of Maxxyz Manager Schedule name #
    '''
    result = await self.sendCmd(f'SchName {scheduleNumber}')
    return result.data[0] or ''

  async def setSchedulerToUseCalendar(self):
    '''
    SchUseCalendar
    Set the Scheduler to use the Calendar Rules
    '''
    return await self.sendCmd(f'SchUseCalendar')

  async def setDate(self, yyyy, mm, dd):
    '''
    SetDate
    Set the Remote computer date (setdate YYYY,MM,DD)
    Example setdate 2006,07,30  will set the date for  July 30 2006
    '''
    return await self.sendCmd(f'SetDate {yyyy},{mm},{dd}')

  async def setPositionDecimal(self, lat: float, lon: float):
    '''
    SetPosDec
    Set the geographical position in decimal value (setposdec Latitude,N or S,Longitude,E or W)
    Example setposdec 45.5,N,34.3,E
    '''
    directionLat = 'N'
    directionLon = 'E'
    if lat < 0:
      directionLat = 'S'
      lat = -lat

    if lon < 0:
      directionLon = 'W'
      lon = -lon

    return await self.sendCmd(f'SetPosDec {lat},{directionLat},{lon},{directionLon}')

  # NOT IMPLEMENTED
  # async def sendSetPosDMS(  ) :
  #   '''
  #   SetPosDMS
  #   Set the geographical position in degre,minute,second value (setposdms DD,MM,SS,N or S,DD,MM,SS,E or W)
  #   Example setposdms 45,30,00,N,34,15,00,W
  #   '''
  #   result = await self.sendCmd(f'SetPosDMS')
  #   return result

  async def setCueListLevel(self, cueList: OnyxCueList, level):
    '''
    SetQLLevel
    [SetQLLevel #,#] -Set Cuelist level where first # is the Cuelist Number and second # is a level between 0 and 255r
    '''
    cueList._transitioning_to = True
    self._notify()
    return await self.sendCmd(f'SetQLLevel {cueList.num},{level}')

  async def setTime(self, hh, mm, ss):
    '''
    SetTime
    Set the Remote computer time (settime HH,MM,SS) is 24 hours format
    Example settime 19,13,30  will set the time for 7:13:30 PM
    '''
    return await self.sendCmd(f'SetTime {hh},{mm},{ss}')

  async def setTimePreset(self, presetNumber, hh, mm, ss):
    '''
    SetTimepreset
    Set the time of a Time Preset No,H,M,S (24 hours values)
    Example  timepreset 1,16,55,30  will set time preset 1 @ 4:55:30 PM
    '''
    return await self.sendCmd(f'SetTimepreset {presetNumber},{hh},{mm},{ss}')

  async def getStatus(self):
    '''
    Status
    [Status] -Will return a status report
    '''
    return await self.sendCmd(f'Status')

  async def getTimePresets(self):
    '''
    TimePresetList
    Return a list of time preset
    '''
    return await self.sendCmd(f'TimePresetList')


def parse_cuelist(parent: ObsidianOnyx, s: str) -> OnyxCueList:
  match = cuelist_info_search.match(s)
  if match:
    num, name = match.groups()
    return OnyxCueList(parent, num, name)
  return None
