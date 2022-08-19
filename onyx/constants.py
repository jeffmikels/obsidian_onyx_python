# This data is what Onyx Returns for CmdList
# and is placed here for easier development

# SCHEDULE COMMANDS
from . import OnyxCueList


START_SCHEDULER = "00001"
START_SCHEDULER_NO_TRACKING = "00004"
START_SCHEDULER_NO_STARTUP = "00005"
RESTART_SCHEDULER_IN = "00006"
RESTART_SCHEDULER_AT = "00007"
STOP_SCHEDULER = "00002"
USE_CALENDAR_RULES = "00003"
IGNORE_CALENDAR_RULES_FOR = "00008"
IGNORE_CALENDAR_RULES_UNTIL = "00009"
STOP_ANY_WAITING_COMMANDS = "00010"

# GENERAL COMMANDS
RESTORE_ALL_WINDOWS = "00020"
RESTORE_ONYX_SCHEDULER_LAUNCHER = "00021"
HIDE_ALL_WINDOWS = "00022"
CLOSE_ALL_WINDOWS = "00023"
SAVE_LOG = "00025"
RESTORE_ALL_TOUCH_PANELS = "00031"
CLOSE_ALL_TOUCH_PANELS = "00032"
LOCK_ALL_TOUCH_PANELS = "00080"
UNLOCK_ALL_TOUCH_PANELS = "00081"
CLOSE_CURRENT_PANEL = "00082"
MINIMIZE_CURRENT_TOUCH_PANEL = "00083"
MINIMIZE_ALL_TOUCH_PANELS = "00087"
MAXIMIZE_ALL_TOUCH_PANELS = "00088"
RESTORE_ALL_TOUCH_PANELS_2 = "00089"
RESET_TOGGLE_CURRENT_TOUCH_PANEL = "00085"
RESET_TOGGLE_ALL_TOUCH_PANELS = "00086"

# WINDOW CONTROLS
SHOW_ACTION_ITEMS_LIST = "00033"
CLOSE_ACTION_ITEMS_LIST = "00034"
OPEN_SCHEDULER = "00041"
CLOSE_SCHEDULER = "00042"
OPEN_CALENDAR_RULES = "00047"
CLOSE_CALENDER_RULES = "00048"
OPEN_CALENDAR_EXPLORER = "00049"
CLOSE_CALENDAR_EXPLORER = "00050"
OPEN_IMAGES_LIST = "00073"
CLOSE_IMAGES_LIST = "00074"
OPEN_COPY_BUTTON_FILTER = "00075"
CLOSE_COPY_BUTTON_FILTER = "00076"
OPEN_QUICK_PANEL = "00077"
CLOSE_QUICK_PANEL = "00078"
