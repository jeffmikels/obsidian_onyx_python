class ObsidianOnyxError(Exception):
  """Raised when Obsidian Onyx API request ended in error.
  Attributes:
      status_code - error code returned by Obsidian Onyx
      status - more detailed description
  """

  def __init__(self, status_code, status):
    self.status_code = status_code
    self.status = status
